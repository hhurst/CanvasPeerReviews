######################################
# Import various class definitions and other modules
errormsg=""
from datetime import datetime, timedelta
try:
	from canvasapi import Canvas
except Exception:
	errormsg+="Missing canvasapi module.  Run 'pip install canvasapi' to intall\n"
from CanvasPeerReviews.creation import Creation
from CanvasPeerReviews.student import Student
from CanvasPeerReviews.comparison import Comparison
from CanvasPeerReviews.assignment import GradedAssignment
from CanvasPeerReviews.parameters import Parameters
from CanvasPeerReviews.review import Review
try:
	from dill.source import getsource	
	import dill
except ImportError: 
	errormsg+="Missing dill module.  Run 'pip3 install dill' to intall\n"
try:
	import pickle
except ImportError:
	errormsg+="Missing pickle module.  Run 'pip3 install pickle5' to intall\n"
try:
	import numpy as np
except ImportError:
	errormsg+="Missing numpy module.  Run 'pip3 install numpy' to intall\n"
try:
	from colorama import Fore, Back, Style
except ImportError:
	errormsg+="Missing colorama module.  Run 'pip3 install colorama' to intall\n"
try:
	import readchar
except ImportError:
	errormsg+="Missing readchar module.  Run 'pip3 install readchar' to intall\n"

import webbrowser
import copy
import random
import sys, os
import subprocess
import csv
import math
import time
import inspect
import threading
import pytz
import warnings
if errormsg!="":
	raise Exception(errormsg)
homeFolder = os.path.expanduser('~')
try:
	from credentials import *
	DATADIRECTORY=homeFolder  + RELATIVE_DATA_PATH
	writeCredentials=False
except Exception:
	writeCredentials=True
if 'verificationKey' not in locals():
	verificationKey=""
	
######################################
# Define some global variables to be used in this module
studentsById=dict()
reviewsById=dict()
creationsByAuthorId=dict()
reviewsByCreationId=dict()
params=Parameters()
students=[]
creations=[]
creationsById=dict()
solutionURLs=dict()
graded_assignments=dict()
lastAssignment=None
nearestAssignment=None
assignmentByNumber=dict()
professorsReviews=dict()
course=None
criteriaDescription=dict()
sections=dict()
params=Parameters()
status={'message': '',
	'err': '', 
	'initialized': False, 
	'gotParameters': False,
	'gotStudentsWork': False, 
	'gotGradedAssignments': False, 
	'gotMostRecentAssignment': False,
	'gotStudents': False,
	'gotSolutionURLs': False,
	'gotReviews': False,
	'calibrated': False,
	'graded': False,
	'regraded': False,
	'posted': False,
	'printedUndoInfo': False,
	'verificationKey': verificationKey,
	'dataDir': './'}

		
	
dataToSave={
	'students': False,
	'assignments': False,
	'parameters': False,
	'reviews': False,
}
keywordReview="recalculate" # if this keyword is in a student comments flag the submission for a regrade
keywordCreation="regrade" # if this keyword is in a student comments flag the submission for a regrade

######################################
# time how long a function takes
def timer(func):
	def wrap(*args, **kwargs):
		start = time.time()
		result = func(*args, **kwargs)
		end = time.time()
		#print(func.__name__, end-start)
		return result
	return wrap


######################################
# Try loading any cached data
@timer
def loadCache():
	global course, status, params, dataDir, students, graded_assignments, reviewsById, reviewsByCreationId
	status['prefix']="course_" + str(course.id) + "_"
	status['message']=""
	loadedData=[]
	try:
		with open( status['dataDir'] +"PickleJar/"+ status['prefix']+'students.pkl', 'rb') as handle:
			students=pickle.load(handle)
		loadedData.append("student data")
	except Exception:
		status['students']="not loaded"
		status['message']+="Unable to find '" +status['dataDir'] +"PickleJar/"+ status['prefix']+'students.pkl' +"'.\nThis file contains student peer review calibation data from \nany past calibrations. If you have done previous calibrations,\nyou should launch python from the directory containing the file\n"
	for student in students:
		studentsById[student.id]=student
	try:
		with open( status['dataDir'] +"PickleJar/"+status['prefix']+'assignments.pkl', 'rb') as handle:
			_graded_assignments=pickle.load(handle)
		graded_assignments.update(_graded_assignments)
		loadedData.append("assginment data")
	except Exception:
		status['message']+="Unable to find 'assignments.pkl'.\nThis file contains grading status of any previously graded assignments.\n  You should launch python from the directory containing the file\n"
	makeAssignmentByNumberDict()
	try:
		with open( status['dataDir'] +"PickleJar/"+status['prefix']+'reviews.pkl', 'rb') as handle:
			[_reviewsById,_reviewsByCreationId, _professorsReviews]=pickle.load(handle)
		reviewsById.update(_reviewsById)
		reviewsByCreationId.update(_reviewsByCreationId)
		professorsReviews.update(_professorsReviews)
		loadedData.append("review data")
	except Exception:
		status['message']+="Unable to find 'reviews.pkl'.\nThis file contains grading status of any previously graded assignments.\n  You should launch python from the directory containing the file\n"
	try:
		with open(status['dataDir'] +"PickleJar/"+ status['prefix']+'parameters.pkl', 'rb') as handle:
			params = pickle.load(handle)
		params.loadedFromFile=True
	except Exception:
		params=Parameters()
		params.loadedFromFile=False 
	status['message']+="\nloaded " + ", ".join(loadedData)

######################################
# delete the files that cache student data and parameters
def reset():
	global status
	try:
		os.remove(status['dataDir'] +"PickleJar/"+ status['prefix']+'students.pkl')
	except Exception:
		pass
	try:
		os.remove(status['dataDir'] +"PickleJar/"+ status['prefix']+'parameters.pkl')
	except Exception:
		pass
	try:
		os.remove(status['dataDir'] +status['prefix']+'solution urls.csv')
	except Exception:
		pass

######################################
# get the course data and return students enrolled, a list of assignments 
# with peer reviews and submissions and the most recent assignment
@timer
def initialize(CANVAS_URL=None, TOKEN=None, COURSE_ID=None, dataDirectory="./Data/", update=False):
	global course, canvas, students, graded_assignments, status, nearestAssignment, keyboardThread
	status['dataDir']=dataDirectory
	status['prefix']=str(COURSE_ID)
	if not os.path.exists(dataDirectory):
		os.makedirs(dataDirectory)
	
	printCommand=False
	if (CANVAS_URL==None or COURSE_ID==None):
		success=False
		while not success:
			try:
				response=input("Enter the full URL for the homepage of your course: ")
				parts=response.split('/courses/')
				CANVAS_URL=parts[0]
				COURSE_ID=int(parts[1].split('/')[0])
				printCommand=True
				success=True
			except:
				print("\nThat wasn't a valid URL for a canvas course.  It should look like https://sjsu.instructure.com/courses/314159")
	if (TOKEN==None):
		print("\nGo to canvas->Account->Settings and from the 'Approved Integrations' section, select '+New Acess Token'")
		print("More info at https://community.canvaslms.com/t5/Admin-Guide/How-do-I-manage-API-access-tokens-as-an-admin/ta-p/89")
		TOKEN=input("Enter the token here: ")
		print()
		printCommand=True
	canvas = Canvas(CANVAS_URL, TOKEN)
	course = canvas.get_course(COURSE_ID)
	if printCommand:
		if  'setup' not in status:
			print("\nIn the future you can use \n\tinitialize('" +CANVAS_URL+ "', '"+TOKEN+"', " + str(COURSE_ID) +")"+"\nto avoid having to reenter this information\n")
		if 	writeCredentials==True:
			print("Generating a credentials template file to use in the future")
			f = open("credentials.py", "a")
			f.write("# credentials automatically generated ["+str(datetime.now())+"] for the canvas course to be used by the other python scripts int his folder\n"
				+ "COURSE_ID = " +str(COURSE_ID) +" #6 digit code that appears in the URL of your canvas course\n"
				+ "CANVAS_URL = '" + CANVAS_URL + "'\n"
				+ "TOKEN = '" + TOKEN+  "' # the canvas token for accessing your course.  See https://community.canvaslms.com/t5/Admin-Guide/How-do-I-obtain-an-API-access-token-in-the-Canvas-Data-Portal/ta-p/157\n"
				+ "RELATIVE_DATA_PATH='" + os.path.abspath(dataDirectory).replace(homeFolder,"")+"/" + "' # location of data directory relative to home directory.  Example '/Nextcloud/Phys 51/Grades/CanvasPeerReviews/Data/'\n"
			)
			f.close()
	loadCache()
	if 'setup' not in status:
		printLine(status['message'],False)
	
	if update or "assginment data" not in status['message'] or "student data" not in status['message']:
		updateAssignmentsAndStudents()
	else:
		initThread = threading.Thread(target=updateAssignmentsAndStudents, args=(True,))
		initThread.start()
		#initThread.join()
	
	lastAssignment =getMostRecentAssignment()
	nearestAssignment =getMostRecentAssignment(nearest=True)
	if lastAssignment != nearestAssignment and lastAssignment!=None:
		print("last assignmetn was " + lastAssignment.name + " but " + nearestAssignment.name + " is closer to the due date")
	for student in students:
		sections[student.section]=student.sectionName
		for key in student.creations:
			creationsById[student.creations[key].id]=student.creations[key]
	status["initialized"]=True
	if "TEST_ENVIRONMENT" in locals() or 'TEST_ENVIRONMENT' in globals() and TEST_ENVIRONMENT:
		CANVAS_URL=CANVAS_URL.replace(".instructure",".test.instructure")
		print(Fore.RED +  Style.BRIGHT +  "\nUsing test environment\nset TEST_ENVIRONMENT=False in 'credentials.py' to change" + Style.RESET_ALL)
		testDir=status['dataDir'][:-1]+"-test/"
		cmd="cp -r '" + status['dataDir'] + "' '" + testDir + "'"
		os.system(cmd)
		status['dataDir'] = testDir
		print("Copying data into temporary data directory at \n\t'" + status['dataDir'] + "'")
	else:
		print("\nUsing production environment\nset TEST_ENVIRONMENT=True in 'credentials.py' to change")
		
	return students, graded_assignments, lastAssignment

def updateAssignmentsAndStudents(quiet=False):
	global status, nearestAssignment, lastAssignment					
	if not quiet:
		printLine("Getting students",False)
	getStudents(course)
	if not quiet:
		printLine("Getting assignments",False)
	getGradedAssignments(course)
	lastAssignment =getMostRecentAssignment()
	nearestAssignment =getMostRecentAssignment(nearest=True)
	if lastAssignment != nearestAssignment and not quiet and lastAssignment!=None:
		print("last assignmetn was " + lastAssignment.name + " but " + nearestAssignment.name + " is closer to the due date")



######################################
# Record what section a student is in
def assignSections(students):
	sections=course.get_sections()
	for section in sections:
		sectionUsers=section.get_enrollments()
		for user in sectionUsers:
			for student in students:
				if user.user_id == student.id:
					student.section=section.id
					student.sectionName=section.name

######################################
# Given an assignment object this will return all of the student submissions
# to that assignment as an array of objects
@timer
def getStudentWork(thisAssignment='last', includeReviews=True):
	global creations, graded_assignments, status
	if not status['initialized']:
		print("Error: You must first run 'initialize()' before calling 'getStudentWork'")
		return
	if thisAssignment=='last':
		if graded_assignments['last'] ==[]:
			for key in 	graded_assignments:
				try:
					print(key, graded_assignments[key].name)
				except Exception:
					pass
			val=int(input("Choose the assignment id to grade: "))
			graded_assignments['last']=graded_assignments[val]
		thisAssignment=graded_assignments['last']
	printLine("Getting submissions for " + thisAssignment.name,False)
	submissions=thisAssignment.get_submissions()
	clearList(creations)
	i=0
	try:
		temp=submissions[0]
	except:
		print("Error getting submissions.  See https://stackoverflow.com/questions/31708519/request-returns-bytes-and-im-failing-to-decode-them")
		print("It may be fixed by running 'pip install brotlipy'")
	for submission in submissions:
		i+=1
		try:
			author=studentsById[submission.user_id]
			submission.courseid=thisAssignment.course_id # this had been .courseid
			submission.reviewCount=0
			submission.author_id=submission.user_id
			author.submissionPlaceholders[thisAssignment.id]=submission
			if not submission.missing and submission.submitted_at!=None:
				creations.append(Creation(submission))
				author.creations[thisAssignment.id]=creations[-1]
				creationsByAuthorId[submission.user_id]=creations[-1]
				#printLine("Getting submission of " + studentsById[submission.user_id].name ,False)
		except Exception:
			status['err']="key error"
	if includeReviews:
		printLine("Getting reviews for " + thisAssignment.name,False)
		getReviews(creations)
		for c in creations:
			c.reviewCount=len([s for s in students if s.assignedReviewOfCreation(c)])
			creationsById[c.id]=c
			#thisAssignment
		printLine("",False)
		print("\r",end="")
	status["gotStudentsWork"]=True

######################################
# Go through all of the assignments for the course and return an array of objects
# from only those assignments that are set up to require peer reviews and
# already have student submissions. 
@timer
def getGradedAssignments(course):
	global graded_assignments, assignments
	assignments = course.get_assignments()
	for i,assignment in enumerate(assignments):
		if (assignment.peer_reviews):
			assignment.courseid=course.id
			if not assignment.id in graded_assignments: # no need to recreate if it was already loaded from the cache
				graded_assignments[assignment.id]=GradedAssignment(assignment)
			else:
				graded_assignments[assignment.id].sync(assignment)
	makeAssignmentByNumberDict()
	dataToSave['assignments'] = True 
	status["gotGradedAssignments"]=True

######################################
# make a dictionary object of graded assignments indexed by the number
def makeAssignmentByNumberDict():
	global graded_assignments
	for key in graded_assignments:
		try:
			if int(''.join(list(filter(str.isdigit,graded_assignments[key].name)))) not in assignmentByNumber:
				assignmentByNumber[int(''.join(list(filter(str.isdigit,graded_assignments[key].name))))]=graded_assignments[key]
		except Exception:
			pass
			#status['message']+="\nUnable to add '" + graded_assignments[key].name + "' to assignmentByNumber"


######################################
# Return the most recently due assignment of all the assignments that have peer reviews
@timer
def getMostRecentAssignment(nearest=False):
	#if nearest=True it will get the assignment with a due date closest to now, regardless of whether it is past due or not yet due
	global lastAssignment
	theAssignment=None
	if len(graded_assignments)==0:
		getGradedAssignments(course)
	minTimeDelta=3650*24*3600
	for key, graded_assignment in graded_assignments.items():
		if key!='last':
			delta=graded_assignment.secondsPastDue()
			if nearest and delta<0:
				delta*=-1
			if (delta > 0  and delta < minTimeDelta and graded_assignment.published) :
				minTimeDelta=delta
				theAssignment=graded_assignment
	if not nearest:
		graded_assignments['last']=theAssignment
	if theAssignment==None:
		print("Couldn't find an assignment with peer reviews that is past due.")
	status["gotMostRecentAssignment"]=True
	return theAssignment	

######################################
# Delte an assignment to work on
def removeAssignment(a=None): 
	if a==None:
		print("This will remove an assignment from the list of graded assignments with peer reviews.  It will NOT delete it from canvas.  ")
		a=chooseAssignment(prompt="choose an assignmetn to remove: ")
	graded_assignments.pop(a.id)
	saveData(['assignments'])
	
######################################
# Choose an assignment to work on
def chooseAssignment(requireConfirmation=True, allowAll=False, timeout=None, defaultAssignment=None, defaultPrompt="last assignment", prompt=None, key=None, filter=None):
	global graded_assignments, lastAssignment, activeAssignment, params
	if key!=None and key in graded_assignments:
		return graded_assignments[key]
	if defaultAssignment==None:
		defaultAssignment=graded_assignments['last']
	if filter==None:
		filteredAssignments=graded_assignments
	else:
		filter+="!"
		# filter of the form "include!exclude"
		filteredAssignments={key: graded_assignments[key] for key in graded_assignments if key!='last' and filter.split("!")[0] in graded_assignments[key].name and (filter.split("!")[1] =="" or not filter.split("!")[1] in graded_assignments[key].name)}
	if 'filter' in dir(params) and params.filter!=None:
		print(f"Filtering assignment list based on {params.filter=} set to None to disable")
		filter=params.filter+"!"		
		filteredAssignments={key: filteredAssignments[key] for key in filteredAssignments if key!='last' and filter.split("!")[0] in filteredAssignments[key].name and (filter.split("!")[1] =="" or not filter.split("!")[1] in filteredAssignments[key].name)}
		
		
		
	confirmed=False
	defaultChoice=None
	msg=""
	while not confirmed:
		codes=[chr(i+65) for i in range(26)]
		for j in range(26):
			codes+=[chr(j+65)+chr(i+65) for i in range(26)]
		i=0
		assignmentKeyByNumber=dict()
		print("\nAssignments with peer reviews enabled\n(update) to update assignments and students lists: ")
		cacheData=[]
		assignmentIDswithNumbers=[assignmentByNumber[i].id for i in assignmentByNumber]
		if allowAll:
			print("\t0) All" )
		for key in filteredAssignments:
			if  key in assignmentIDswithNumbers:
				iStr=str([num for num in assignmentByNumber if assignmentByNumber[num]==graded_assignments[key] ][0]) +")"
			else:
				iStr=codes[i]+")"
				if (key != 'last'):
					i+=1		
			if (key != 'last'):
				cacheData.append({'str':iStr, 'name': graded_assignments[key].name, 'key': key})
				if graded_assignments[key] == defaultAssignment:
					print(f"\t{Fore.BLUE}{iStr:<4}{graded_assignments[key].name}{Style.RESET_ALL}  <---- {defaultPrompt}")
					defaultChoice=iStr[:-1]
				else:
					print(f"\t{iStr:<4}{graded_assignments[key].name}")
				assignmentKeyByNumber[iStr[:-1]]=key
		val=None
		while not (val in assignmentKeyByNumber or (val=='0' and allowAll)):
			if timeout==None or defaultChoice==None:
				if prompt==None and defaultChoice==None:
					prompt=f"Enter a choice for the assignment to work on: "
				elif prompt==None:
					prompt=f"Enter a choice for the assignment to work on [{defaultChoice}]: "
				val=input(prompt).upper()
			else:
				if prompt==None:
					prompt="Enter a choice for the assignment to work on"
				val=inputWithTimeout(prompt, default=defaultChoice, timeout=timeout).upper()					
			if val=="":
				val=defaultChoice
			elif val.lower()=='update':
				updateAssignmentsAndStudents()
				key=None
				activeAssignment=chooseAssignment(requireConfirmation, allowAll, timeout, defaultAssignment, defaultPrompt, prompt, key, filter)
				return activeAssignment
		if requireConfirmation:
			if allowAll and val=='0':
				confirmed=confirm("You have chosen all assignments")
			else:
				confirmed=confirm("You have chosen " + graded_assignments[assignmentKeyByNumber[val]].name)
		else:
			confirmed=True
		if confirmed:
			if val=='0':
				activeAssignment="all"
			else:
				activeAssignment=graded_assignments[assignmentKeyByNumber[val]]
	os.system("mkdir -p '" + status['dataDir'] + "PickleJar" + "'")
	return activeAssignment

######################################
#This function assigns a peer review and records it
recentlyAssignedPeerReviews=[]
def assignAndRecordPeerReview(creation,reviewer, msg=""):
	if not status['printedUndoInfo']:
		print(Style.BRIGHT + "\nTo delete any assigned peer reviews run 'undoAssignedPeerReviews()'.  You will be prompted to delete each review that has been assigned in this session.\n" + Style.RESET_ALL)
		status['printedUndoInfo']=True
	peer_review=creation.create_submission_peer_review(reviewer.id)
	recentlyAssignedPeerReviews.append(peer_review)
	reviewer.recordAssignedReview(creation.assignment_id, peer_review)
	creation.reviewCount+=1
	printLeftRight("assigning " + str(reviewer.name)	 + " to review " + str(studentsById[creation.author_id].name) + "'s creation ", msg)	
	return peer_review
	
def undoAssignedPeerReviews(author=None, reviewer=None, assignment=None, peer_review=None):
	val="null"
	for thePeerReview in recentlyAssignedPeerReviews:
		theReviewer=studentsById[thePeerReview.assessor_id]
		theCreation=[creation for creation in creations if creation.id==thePeerReview.asset_id][0]
		theAuthor=studentsById[theCreation.author_id]
		theAssignment=graded_assignments[theCreation.assignment_id]
		if (author==None or author==theAuthor) and (reviewer==None or reviewer==theReviewer) and (assignment==None or assignment==theAssignment) and (peer_review==None or peer_review==thePeerReview):
			if val.upper() != val:
				print(f"{theReviewer.name}'s assigned review of {theAuthor.name}'s creation on {theAssignment.name}")
				val = input("(y) to delete this one, (Y) to delete all?")
			if val.lower()=="y":
				deleteReview(thePeerReview)
		
######################################
#This takes a list of submissions which are to be used as calibration reviews
# and assigns one to each student in the class, making sure to avoid assigning
# a calibration to its own author if possible
def assignCalibrationReviews(calibrations="auto", assignment="last"):
	global status, creations
	returnVal=""
	if assignment=="last":
		assignment=graded_assignments['last']
	if not status['initialized']:
		print("Error: You must first run 'initialize()' before calling 'assignCalibrationReviews'")
		return
	elif not status['gotStudentsWork']:
		print("getting student work")
		getStudentWork(assignment)
	studentsWithSubmissions=[studentsById[c.author_id] for c in creations if c.author_id in studentsById and studentsById[c.author_id].role=='student']
	if calibrations=="auto":
		calibrations=[]
		try:
			print("professor reviews for ", assignment.name, assignment.id)
			professorReviewedSubmissionIDs=[r.submission_id for r in professorsReviews[assignment.id]]
			calibrations=[c for c in creations if (c.id in professorReviewedSubmissionIDs)]
		except:
			print("It looks like the professor hasn't yet graded any submissions.  You should grade at least one to use as a calibration review.")
		#return
		if len(calibrations)==0 and confirm("There were no submissions reviewed by the professor, should a random submission be assigned as the calibration review?"):
			calibrations=="random"
	if calibrations=="autobysection": #for each section find professor reviewed submissions to use as calibration, but randomly pick one if none is found
		calibrations=[]
		for sectionKey in sections:
			print("professor reviews for ", assignment.name, assignment.id, "in section", sections[sectionKey])
			professorReviewedSubmissionIDs=[r.submission_id for r in professorsReviews[assignment.id] if studentsById[r.author_id].section==sectionKey]
			calibrationsThisSection=[c for c in creations if (c.id in professorReviewedSubmissionIDs)]
			if len(calibrationsThisSection)==0:
				creationsToConsider=randomize([c for c in creations if studentsById[c.author_id].section == sectionKey and  c.author_id in studentsById and studentsById[c.author_id].role=='student'])
				thisCalibration=None
				for c in creationsToConsider:
					if studentsById[c.author_id].role=='student':# and c.submitted_at != None:# and len(c.assignedPeerReviews())==0:
						thisCalibration=c
						break
				if thisCalibration == None:
					print(f"Unable to find a suitable creation to use as a calibration in {sections[sectionKey]}")
				else:
					calibrations.append(thisCalibration)
					#unreviewedSubmissions=[c for c in creations if len(c.assignedPeerReviews())==0 and c.submitted_at != None and studentsById[c.author_id].role=='student']
					#calibrations=random.choice(studentsWithSubmissions)
					msg=f"{studentsById[thisCalibration.author_id].name} has  been chosen as the calibration review for {assignment.name} in {sections[sectionKey]}"
					print(msg)
					log(msg)
			else:
				calibrations+=calibrationsThisSection	
	if calibrations=="random":
		calibrations=[]
		for sectionKey in sections:
			creationsToConsider=randomize([c for c in creations if studentsById[c.author_id].section == sectionKey and  c.author_id in studentsById and studentsById[c.author_id].role=='student'])
			print("Looking for submissions with no peer reviews ... this may take some time...")
			thisCalibration=None
			for c in creationsToConsider:
				if studentsById[c.author_id].role=='student':# and c.submitted_at != None:# and len(c.assignedPeerReviews())==0:
					thisCalibration=c
					break
			if thisCalibration == None:
				print(f"Unable to find a suitable creation to use as a calibration in {sections[sectionKey]}")
			else:
				calibrations.append(thisCalibration)
				#unreviewedSubmissions=[c for c in creations if len(c.assignedPeerReviews())==0 and c.submitted_at != None and studentsById[c.author_id].role=='student']
				#calibrations=random.choice(studentsWithSubmissions)
				msg=f"{studentsById[thisCalibration.author_id].name} has  been chosen as the calibration review for {assignment.name} in {sections[sectionKey]}"
				print(msg)
				log(msg)		
	reviewers=randomize(studentsWithSubmissions) 
	calibrations=makeList(calibrations)
	if len(calibrations)==0:
		print("Unable to find a suitable creation to use as a calibration...none assigned")
		return []
	print("Professor has already graded submissions by ", end="")
	for c in calibrations:
		if c!=calibrations[-1]:
			print(" " + studentsById[c.author_id].name,end=",")
		else:
			print(" and " + studentsById[c.author_id].name)			

	i=0
	for j, reviewer in enumerate(reviewers):
		tic=time.time()
		i+=1
		iStart=i
		#while (	time.time()-tic < 1 and ((reviewer.id == calibrations[i%len(calibrations)].author_id) or  (studentsById[reviewer.id].section != studentsById[calibrations[i%len(calibrations)].author_id].section ))):
		while (	(i < iStart +len(students) + 1) and ((reviewer.id == calibrations[i%len(calibrations)].author_id) or  (studentsById[reviewer.id].section != studentsById[calibrations[i%len(calibrations)].author_id].section ))):
			i+=1
		#if not time.time()-tic  <1:
		#	raise Exception("Timeout error assigning calibration reviews - perhaps the professor hasn't yet graded an assignment from each section?")
		#	return []
		calibration = calibrations[i%len(calibrations)]
		author=studentsById[calibrations[i%len(calibrations)].author_id]
		if (author.name!=studentsById[reviewer.id].name):
			msg=str(j+1) + "/" + str(len(reviewers))
			peer_review=assignAndRecordPeerReview(calibration,reviewer, msg)
		else:
			printLine("skipping self review", newLine=False)
	dataToSave['students']=True
	return calibrations
	
######################################
# Takes a student submission and a list of potential reviewers, and the number of reviews 
# to assign and then interacts with canvas to assign that number of reviewers to peer
# review the submission.  It will select reviewers from the beginning of the list of
# potential reviewers skipping over anyone who has already been assigned at least the
# target number of reviews.
def assignPeerReviews(creationsToConsider, reviewers="randomize", numberOfReviewers=4, AssignPeerReviewsToGraderSubmissions=False):
	startTime=time.time()
	global status
	if not status['initialized']:
		print("Error: You must first run 'initialize()' before calling 'assignPeerReviews'")
		return
	elif not status['gotStudentsWork']:
		getStudentWork()
		
	if AssignPeerReviewsToGraderSubmissions:
		creationsToConsider=makeList(creationsToConsider) #set this to false if you want the graders submissions to be peer reviewed
	else:
		creationsToConsider=[c for c in makeList(creationsToConsider) if studentsById[c.author_id].role=='student']
	studentsWithSubmissions=[studentsById[c.author_id] for c in creationsToConsider if studentsById[c.author_id].role=='student']
	graders=[x for x in students if x.role=='grader']
	graders=randomize(graders)
	if reviewers=="randomize":
		studentsWithSubmissions=randomize(studentsWithSubmissions) 
	reviewers=makeList(studentsWithSubmissions)
	#assign params.numberOfReviews reviews per creation
	for i, creation in enumerate(creationsToConsider):
		for j,reviewer in enumerate(reviewers):
			if (reviewer.numberOfReviewsAssignedOnAssignment(creation.assignment_id) < params.numberOfReviews and creation.reviewCount < numberOfReviewers and reviewer.id != creation.user_id and reviewer.section == studentsById[creation.user_id].section):
				msg=str(i+1) + "/" + str(len(creationsToConsider))
				peer_review=assignAndRecordPeerReview(creation,reviewer, msg)
		reviewerAvaialble=creation.reviewCount<len(creationsToConsider)-1
		while creation.reviewCount < numberOfReviewers and reviewerAvaialble: #this creation did not get enough reviewers assigned somehow
			#get the reviewer with the fewest reviews so far
			sortedReviewers=sorted(reviewers, key=lambda r:r.numberOfReviewsAssignedOnAssignment(creation.assignment_id))
			sortedAvailableReviewers=[reviewer for reviewer in sortedReviewers if (not reviewer.assignedReviewOfCreation(creation)) and reviewer.id != creation.user_id and reviewer.numberOfReviewsAssignedOnAssignment(creation.assignment_id)  < params.numberOfReviews+1 and reviewer.section == studentsById[creation.user_id].section]
			reviewerAvaialble=len(sortedAvailableReviewers)>0
			if reviewerAvaialble:
				reviewer=sortedAvailableReviewers[0]
				msg="additional assignment " + str(i+1) + "/" + str(len(creationsToConsider))
				peer_review=assignAndRecordPeerReview(creation,reviewer, msg)
	# now that all creations have been assigned the target number of reviews, keep assigning until all students have the target number of reviews assigned
	for reviewer in reviewers:
		tic=time.time()
		print(f"{reviewer.name} was assigned {reviewer.numberOfReviewsAssignedOnAssignment(creationsToConsider[0].assignment_id)} reviews")
		while (reviewer.numberOfReviewsAssignedOnAssignment(creationsToConsider[0].assignment_id)  < params.numberOfReviews and reviewer.numberOfReviewsAssignedOnAssignment(creationsToConsider[0].assignment_id) < len(creationsToConsider)-1 and time.time()-tic < 1):
			creation=random.choice(creationsToConsider)
			if (reviewer.section == studentsById[creation.user_id].section):
				msg="---"
				peer_review=assignAndRecordPeerReview(creation,reviewer, msg)
				#print("assigning " + str(reviewer.name)	 + " to review " + str(studentsById[creation.author_id].name) + "'s creation")			
	if len(graders)==0:
		return
	# finally assign to graders
	sections=dict()
	for grader in graders:
		sections[grader.section] = grader.sectionName
	for key in sections:
		thisSectionsGraders=[x for x in students if (x.role=='grader' and x.section == key)]
		thisSectionsCreations=[x for x in creationsToConsider if (studentsById[x.author_id].section == key)]
		if len(thisSectionsCreations)>0:
			reviewsPerGrader=int(len(thisSectionsCreations)/len(thisSectionsGraders))
			thisSectionsGraders=makeList(thisSectionsGraders)
			#lol(list,sublistSize) takes a list and returns a list-of-lists with each sublist of size sublistSize
			lol = lambda lst, sz: [lst[i:i+sz] for i in range(0, len(lst), sz)] # see https://stackoverflow.com/questions/4119070/how-to-divide-a-list-into-n-equal-parts-python
			creationsListofList=lol(thisSectionsCreations,reviewsPerGrader)
			# if dividing up the list left a few extras, add them to the last element
			if (len(creationsListofList) > len(thisSectionsGraders)):
				creationsListofList[-2] += creationsListofList[-1]
			print("Assigning reviews to graders of ", sections[key])
			for i,reviewer in enumerate(thisSectionsGraders):
				for j,creation in enumerate(creationsListofList[i]):
					if (reviewer.id != creation.user_id ):
						msg=str(j+1) + "." + str(i+1) + "/" + str(len(creationsListofList[i]))
						peer_review=assignAndRecordPeerReview(creation,reviewer, msg)
	dataToSave['students']=True
				
######################################
# Get a list of all students enrolled in the course.  Return an array of Student objects
@timer
def getStudents(course):
	users = course.get_users(enrollment_type=['student'])
	global students
	#clearList(students)
	for user in users:
		user.courseid=course.id
		alreadyAdded=False
		try:
			for student in students:
				if	student.id==user.id:
					alreadyAdded=True
					studentsById[user.id]=student
		except Exception:
			pass
		if not alreadyAdded:
			studentsById[user.id]=Student(user)
			students.append(studentsById[user.id])
	#studentsById[4445567]="Test Student"	
	status["gotStudents"]=True
	needToGetSections=False
	for student in students:
		needToGetSections=needToGetSections or student.section==0
	if 	needToGetSections:	
		printLine("Looking up which section each student is in", False)
		assignSections(students)
	dataToSave['students'] = True
	return students
		
######################################
# Check if the time window for accepting peer reviews for an assignment has passed
def peerReviewingOver(assignment):
	thisDelta=datetime.utcnow()-assignment.due_at_date.replace(tzinfo=None)
	return thisDelta.total_seconds() > params.peerReviewDurationInSeconds()

######################################
# Look for the URL for the assignment solutions in a csv file.	If the file
# isn't found it will generate a template
def getSolutionURLs(assignment=None, fileName="solution urls.csv"):
	global status, solutionURLs
	solutionURLs={}
	fileName=status['dataDir'] + fileName.replace("/","").replace(":","")
	placeholder="solution_URLs_go_here"
	status["gotSolutionURLs"]=True
	print("looking for solution urls in", fileName)
	try:
		success=False
		f = open(fileName, "r")
		lines = f.readlines()
		f.close()
		for line in lines:
			cells=line.split(",")
			if assignment.name in cells[0] and not placeholder in cells[1]:
				solutionURLs[assignment.id]=cells[1].strip()
				success=True
		#append any new assignments
		f = open(fileName, "a")
		for key, newAssignment in graded_assignments.items():
			line=newAssignment.name + ", " + placeholder +"\n"
			if newAssignment.name not in "".join(lines):
				f.write(line)
		f.close()
		if success:
			return solutionURLs[assignment.id]
	except Exception as e: 
		print("Exception - look on lines 702-720 in utilities.py")
		f = open(fileName, "w")
		f.write("Assignment Name, Solution URL\n")
		lines=[]
		for key, assignment in graded_assignments.items():
			line=assignment.name + ", " + placeholder +"\n"
			f.write(line)
			lines.append(line)
		f.close()
		subprocess.call(('open', fileName))
		print("Put the solution URLs into the file '" + fileName + "'")
	return ""

# ######################################
# Delete a given peer review from the canvas assignments
def deleteReview(peer_review):
	reviewer=studentsById[peer_review.assessor_id]
	creation=[creation for creation in creations if creation.id==peer_review.asset_id][0]
	assignment=graded_assignments[creation.assignment_id]
	try:
		reviewer._assignedReviews[assignment.id].remove(peer_review)
	except Exception:
		pass 
	print("deleting " + reviewer.name + "'s peer review assignment of " + studentsById[creation.author_id].name )
	reviewer.removeAssignedReview(peer_review)
	creation.delete_submission_peer_review(peer_review.assessor_id)

# ######################################
# Count how many reviews have been assigned to each student using data from Canvas
def resyncReviews(assignment,theCreations=[]):
	global students
	if len(theCreations)==0:
		getStudentWork(assignment)
		theCreations=creations	
	theCreations=makeList(theCreations)
	for s in students:
		s._assignedReviews[assignment.id]=[]
	print("Checking how many peer reviews each students has already been assigned...")
	for i,creation in enumerate(theCreations):
		printLine("    " +str(i) + "/" + str(len(theCreations)) +" Checking reviews of " + studentsById[creation.author_id].name, False)
		for peer_review in creation.get_submission_peer_reviews():
			if peer_review.assessor_id in studentsById:
				reviewer=studentsById[peer_review.assessor_id]
				reviewer.recordAssignedReview(creation.assignment_id, peer_review)
	printLine("",False)
	
######################################
# create a text summary of a review
def reviewSummary(assessment, display=False):
	global criteriaDescription
	if display:
		print("Review of " + str(assessment['artifact_id']) + " by " +studentsById[assessment['assessor_id']].name+ "\n")
	msg=""
	#get comments on each learning outcome
	for d in assessment.data:
		msg+="\t" + criteriaDescription[d['description']] 
		try:
			msg+=" [" + str(d['points']) + "]"
		except Exception:
			msg+=" [missing]"
		try:
			msg+=" "+d['comments']
		except Exception:
			pass
		msg+="\n"
	#get general comments on the submission	
	c=[c for c in creations if c.id==assessment.submission_id][0]
	ce=c.edit()
	comments=[comment_item['comment'] for comment_item in ce.submission_comments if comment_item['author_id']==assessment.reviewer_id]
	for comment in comments:
		msg+=comment+"\n"
	if display:
		print(msg)
	return msg	

######################################
# Process a given student submission finding all of the peer reviews of that submissions
# those peer reviews get attached to the student objects for both the author of the 
# submission and the students performing the reviews.  Nothing is returned. 
@timer
def getReviews(creations):
	global course, reviewsById, allReviews
	rubrics=course.get_rubrics()
	allReviews=[]
	for rubric in rubrics:
		try:
			rubric=course.get_rubric(rubric.id,include='assessments', style='full')
			if hasattr(rubric, 'assessments'):
				for creation in creations:
					for assessment in rubric.assessments:
						if ((assessment['assessment_type']=='grading' or assessment['assessment_type']=='peer_review') and creation.id == assessment['artifact_id'] ):
							review=Review(assessment, creation, graded_assignments[creation.assignment_id].rubric, graded_assignments[creation.assignment_id])
							reviewsById[review.id]=review
							try:
								reviewer=studentsById[assessment['assessor_id']]						
								for pr in reviewer.assignedReviews(creation.assignment_id):
									if review.author_id==pr.user_id:
										review.peer_review=pr
							except Exception:
								pass
								#print(f"Student with id {assessment['assessor_id']} not in list of students")
							alreadyProcessed = any(thisReview.fingerprint() == review.fingerprint() for thisReview in studentsById[creation.user_id].reviewsReceived)
							if not alreadyProcessed:
								studentsById[creation.user_id].reviewsReceived.append(review)
							else: 
								pass
							if creation.assignment_id in studentsById[creation.user_id].regrade: # replace entry
								for i,thisReview in enumerate(studentsById[creation.user_id].reviewsReceived):
									if thisReview.fingerprint() == review.fingerprint() and assessment['assessment_type']=="grading":
										studentsById[creation.user_id].reviewsReceived[i]=review			
							if creation.id in reviewsByCreationId:
								#reviewsByCreationId[creation.id].append(review)
								reviewsByCreationId[creation.id][review.id]=review
							else:
								reviewsByCreationId[creation.id]={review.id: review}
							if assessment['assessment_type']=='grading':
								if creation.assignment_id in professorsReviews:
									if review.fingerprint() not in [pr.fingerprint() for pr in professorsReviews[creation.assignment_id]]:
										professorsReviews[creation.assignment_id].append(review)
								else:
									professorsReviews[creation.assignment_id]=[review]
							elif review.reviewer_id in studentsById:
								# if not already assigned assignment.multiplier[cid]
								studentsById[review.reviewer_id].reviewsGiven[review.submission_id]=review
							allReviews.append(review)
		except:
			print(f"Unable to get {rubric.title} for this assignment.  Skipping...")
	#create the comparison objects for each student
	for student in students:
		for key,thisGivenReview in student.reviewsGiven.items():
			blankCreation=len([c for c in creations if c.id == key and c.missing])>0
			for cid in thisGivenReview.scores:
				student.criteriaDescription[cid]=criteriaDescription[cid]
			if not blankCreation: 
				if not thisGivenReview.submission_id in reviewsByCreationId:
					print(thisGivenReview.fingerprint() + " was not in  reviewsByCreationId.  Adding.")
					reviewsByCreationId[thisGivenReview.submission_id]=dict()
					reviewsByCreationId[thisGivenReview.submission_id][thisGivenReview.id]=thisGivenReview
				
				for otherReview in reviewsByCreationId[thisGivenReview.submission_id].values():
					alreadyCalibratedAgainst=otherReview.id in student.comparisons
					if (otherReview.reviewer_id != student.id and not alreadyCalibratedAgainst): #don't compare this review to itself and dont repeat a calibration	
						student.comparisons[otherReview.id]=Comparison(thisGivenReview, otherReview, graded_assignments[thisGivenReview.assignment_id], studentsById, params)
	status["gotReviews"]=True
	dataToSave['reviews']=True
	dataToSave['students']=True
	return allReviews
	
######################################
# Compare the peer reviews students gave to the peer reviews of the same submission 
# given by others.	An average deviation is computed using a weighting factor based on 
# the performance of the other students on their previous reviews.	If the submission
# being reviewed was also graded by the instructor, the deviation from the instructor's
# review will more heavily weighted.  The results are save as a "grading power" for the 
# student in the Student object.  This grading power is used for future calibrations,
# and is used as a weighting factor when assigning grades to students they reviewed.
def calibrate(studentsToCalibrate="all", endDate=datetime.utcnow().replace(tzinfo=pytz.UTC)):
	global graded_assignments
	if (studentsToCalibrate=="all"):
		studentsToCalibrate=students
	global status
	if not status['initialized']:
		print("Error: You must first run 'initialize()' before calling 'calibrate'")
		return
	#process the comparisons to get the current grading adjustments
	for student in students:
		student.updateAdjustments(normalize=False, weeklyDegradationFactor=params.weeklyDegradationFactor(), endDate=endDate)		
	#		Now that all of the students grading powers have been updated, normalize everything so that the average
	#		grading power for all of the students is 1
	for cid in list(criteriaDescription) + [0]:
		avg=np.average([s.getGradingPower(cid) for s in students])
		#avg=np.nanmean([s.getGradingPower(cid) for s in students])
		for student in students:
			student.gradingPowerNormalizationFactor[cid]=avg
	for student in students:
		student.updateAdjustments(normalize=True,  weeklyDegradationFactor=params.weeklyDegradationFactor(), endDate=endDate)	

 	# update all of the comparisons with the new grading weights
	for student in studentsToCalibrate:
		for comp in student.comparisons.values():
			if comp.updateable:
				otherReviewer=studentsById[reviewsById[comp.reviewIDComparedTo].reviewer_id]
				comp.updateWeight(otherReviewer)
	dataToSave['students']=True
	status["calibrated"]=True

######################################
# adjust point distribution for a specific assignment
def overrideDefaultPoints(assignment):
	for cid in assignment.criteria_ids():
		val=getNum("How many points (out of 100) should be awarded for '" + criteriaDescription[cid]+ "'?", params.pointsForCid(cid, assignment))
		params.pointsForCid(cid,assignment ,val)
	dataToSave['parameters']=True	

######################################
# Process a list of students (or all of the students, calling the
# gradeStudent function for each
def grade(assignment, studentsToGrade="All", reviewScoreGrading="default"):
	global status
	if not status['initialized']:
		print("Error: You must first run 'initialize()' before calling 'grade'")
		return		
	if isinstance(studentsToGrade, str) and studentsToGrade.lower()=="all":
		studentsToGrade=students
	for student in makeList(studentsToGrade):
		gradeStudent(assignment, student, reviewScoreGrading)
	if reviewScoreGrading=="default":
		val=inputWithTimeout(f"Review grades will use '{assignment.reviewScoreMethod}' method.  (c) to change", 3)		
		if val=='c':
			assignment.setReviewScoringMethod()		
	assignment.graded=True
	status["graded"]=True
	msg=assignment.name +  " graded with the following point values:\n"
	if status["regraded"]:
		msg=assignment.name +  " regraded with the following point values:\n"
	for cid in assignment.criteria_ids():
		msg+= "\t(" +str(params.pointsForCid(cid,assignment ))+ ") " + criteriaDescription[cid] + "\n"
	msg+="Using the following function for review '" + assignment.reviewCurve+ "' and a curve of '" + assignment.curve + "'\n"
	log(msg)
	if isinstance(studentsToGrade, str) and studentsToGrade.lower()=="all":
		getStatistics(assignment, text=False, hist=False)
	dataToSave['assignments']=True
	dataToSave['students']=True

######################################
# Check for any work that is unreviewed.
def checkForUnreviewed(assignment, openPage=False):	
	graderIDs=[x.id for x in students if x.role=='grader']
	mostNumberOfReviewsReceived=0
	for creation in creations:
		student=studentsById[creation.author_id]	
		mostNumberOfReviewsReceived=max(mostNumberOfReviewsReceived,student.numberOfReviewsReceivedOnAssignment(assignment.id))
	creationsByNumberOfReviews=[0]*(mostNumberOfReviewsReceived+1)
	for n in range(mostNumberOfReviewsReceived+1):
		creationsByNumberOfReviews[n]=sorted([c for c in creations if studentsById[c.author_id].numberOfReviewsReceivedOnAssignment(assignment.id)==n and studentsById[c.author_id].role=='student'], key=lambda x: studentsById[x.author_id].sortable_name)
	if len(creationsByNumberOfReviews[0])==0 and len(creationsByNumberOfReviews[1])==0 and len(creationsByNumberOfReviews[2])==0:
		print("All creations have been reviewed at least three times")
	elif len(creationsByNumberOfReviews[0])==0 and len(creationsByNumberOfReviews[1])==0:
		print("All creations have been reviewed at least twice")
	elif len(creationsByNumberOfReviews[0])==0 :
			print("All creations have been reviewed at least once")
	fileName=status['dataDir'] + assignment.name + "_todo.html"
	f = open(fileName, "w")
	f.write("<html><head><title>Submissions by number of completed reviews</title><style>\n")
	f.write(".instructor {color: blue;}\n.grader {color: green;}\n.student {color: black;}\n.nobody {color: #660000;}")
	f.write("a {text-decoration:none}\n")
	f.write("a.instructor:link {color: #0000ff;}\n")
	f.write("a.instructor:hover {color: #440044;}\n")
	f.write("a.grader:link {color: #008000;}\n")
	f.write("a.grader:hover {color: #440044;}\n")
	f.write("a.student:link {color: #000000;}\n")
	f.write("a.student:hover {color: #440044;}\n")
	colors = ["#ffeeee", "#eeeeff"]		
	ind=0
	for key in sections:
		ind=(ind+1)%len(colors)
	f.write("</style></head><body>\n")
	f.write("<h3>Submissions for "+assignment.name+" by number of completed reviews:</h3>\n<ul>\n")
	f.write("<span class='instructor'>Graded by instructor</span> | ")
	f.write("<span class='grader'>Graded by grader</span> | ")
	f.write("<span class='student'>Only graded by peers</span> | ")
	f.write("<span class='nobody'>ungraded</span>\n")
	f.write("<table border='0'><tr>")
	for n in range(mostNumberOfReviewsReceived+1):
		if n==1:
			f.write("<th>" +str(n)+" review (" + str(len(creationsByNumberOfReviews[n]))+  ")</th>")
		else:
			f.write("<th>" +str(n)+" reviews (" + str(len(creationsByNumberOfReviews[n]))+  ")</th>")
	f.write("</tr>\n")
	for n in range(mostNumberOfReviewsReceived+1):
		f.write("<td style='vertical-align:top; white-space: nowrap;'>")
		for section in sorted(list(sections.values())):
			if (len(sections)>1):
				f.write("<hr>")
				f.write("<div class='sec"+section[-2:]+"'>")
				#f.write("Sec "+str(int(section[-2:]))  +"<br>"")
			for creation in creationsByNumberOfReviews[n]:
				gradedByInstructor=len([r for r in studentsById[creation.author_id].reviewsReceived if r.review_type=='grading' and r.assignment_id ==assignment.id])>0
				gradedByGrader=len([r for r in studentsById[creation.author_id].reviewsReceived if r.reviewer_id in graderIDs and r.assignment_id ==assignment.id])>0
				if studentsById[creation.author_id].sectionName == section:
					url=creation.preview_url.replace("assignments/","gradebook/speed_grader?assignment_id=").replace("/submissions/","&student_id=").replace("?preview=1&version=1","")
					f.write("<a href='"+ url +"' target='_blank' class='")
					if (gradedByInstructor):
						f.write("instructor")
					elif gradedByGrader:
						f.write("grader")
					else:
						if n==0:
							f.write("nobody")			
						else:
							f.write("student")			
					f.write( "'> "+studentsById[creation.author_id].name + "</a><br>\n")
			if (len(sections)>1):
				f.write("</div>")
		f.write("</td>\n")
	f.write("</tr></table>\n")
	f.write("</ul></body></html>\n")
	f.close()
	if openPage:
		subprocess.call(('open', fileName))
	return creationsByNumberOfReviews[0]


######################################
# write a template file for the user to later edit
def writeTemplate(fileName="feedback_template.txt"):
		f = open(fileName, "w")
		msg='''#     This is a template file for student feedback on grades
#     variables should be enclosed in curly braces.  Allowable variable are
# 
#		{keywordCreation}
# 		{keywordReview}
#		{points_by_criteria}
#		{description_by_criteria}
#		{creationGrade}
#		{reviewGrade}
#		{rawGrade}
#		{curvedGrade}
# 
#     any line with by_criteria in it will be written
#     multiple times, once for each grading criteria
#########################################################################
# 							user defined variables				 		#
#########################################################################
# one definition per line.  
{comment on review: high grade}=Good job on the reviews.  Keep it up!
{comment on review: low grade}=Your review grade will improve as it aligns more closely with other graders.
{comment on review: no reviews complete}=You didn't complete your peer reviews, so you review score is {reviewGrade}
{comment if grades are curved}=This was curved to give an adjusted score of {curvedGrade}.
{review feedback by criteria: higher scores given}=    {review_rms_by_criteria} points for '{description_by_criteria}' (on average {absolute_value_of_deviation} higher than other reviewers)
{review feedback by criteria: similar scores given}=    {review_rms_by_criteria} points for '{description_by_criteria}' (on average about the same  as other reviewers)
{review feedback by criteria: lower scores given}=    {review_rms_by_criteria} points for '{description_by_criteria}' (on average {absolute_value_of_deviation} lower than other reviewers)

#########################################################################
# 			general feedback with calibrated review grading				#
#########################################################################
A weighted average of the reviews of your work give the following scores:
    {points_by_criteria} for '{description_by_criteria}'

Compared to reviews by the instructor and other students, the peer review scores you gave others deviated by
{review feedback by criteria}
{comment on review}

You earned {creationGrade}% for your submission and {reviewGrade}% for your reviews.   When combined this gives you {rawGrade}%.  {comment if grades are curved}

If you believe the score assigned to your creation is not an accurate reflection of your work, explain in a comment in the next few days and include the word '{keywordCreation}' to have it regraded.

If you believe your review grade does not correspond to the quality of your peer reviewing, you can request to have it recalculated using only comparisons to my reviews.  To have it recalculated enter a comment with the word '{keywordReview}' in it.
#########################################################################
# 				 general feedback ignoring reviews			 			#
#########################################################################
A weighted average of the reviews of your work give the following scores:
    {points_by_criteria} for '{description_by_criteria}'

You earned {creationGrade}% for your submission.  {comment if grades are curved}

If you believe the score assigned to your creation is not an accurate reflection of your work, explain in a comment in the next few days and include the word '{keywordCreation}' to have it regraded.

If you believe your review grade does not correspond to the quality of your peer reviewing, you can request to have it recalculated using only comparisons to my reviews.  To have it recalculated enter a comment with the word '{keywordReview}' in it.

#########################################################################
# 							regrade comments							#
#########################################################################
I've regraded your work.  My review of your work give the following scores:
    {points_by_criteria} for '{description_by_criteria}'
Based on the regrading you earned {creationGrade}% for your submission
which brings your final curved score to {curvedGrade}.

#########################################################################
# 					reminder about peer reviews							#
#########################################################################
I noticed you haven't yet completed any of your assigned peer reivews.  Remember to complete these on time to get credit for them.  Here are instructions on how to submit a peer review in case you need them: 
https://community.canvaslms.com/t5/Student-Guide/How-do-I-submit-a-peer-review-to-an-assignment/ta-p/293
#########################################################################
# 					message about posted solutions						#
#########################################################################
Peer reviews have been assigned and <a href='{solutionsUrl}'>solutions to {assignmentName}</a> have been posted.  Please review the solutions and then complete your peer reviews before the next class meeting."
'''
		f.write(msg)
		f.close()
		return msg

######################################
# read a template file and extract and return the part identified by 'name'
def getTemplate(fileName="feedback_template.txt", name=None):
	global status
	if ("alternativeFeedbackTemplate" in dir(params) and "feedback_template.txt" in fileName):
		fileName=fileName.replace("feedback_template.txt",params.alternativeFeedbackTemplate)
		if "alternativeFeedbackTemplateWarningGiven" not in status:
			print("Using " + fileName + " as an altenrative feedback template")
		status["alternativeFeedbackTemplateWarningGiven"]=True
	try:
		f = open(fileName, "r")
		raw_lines = f.readlines()
		f.close()
	except:
		raw_lines=writeTemplate(fileName)
		print(f"created new template file")
	foundTemplate=False
	for i,line in enumerate(raw_lines):
		if line[0]=="#" and name in line:
			foundTemplate=True
			break
	#clear any commented lines:
	while raw_lines[i][0]=="#":
		i+=1
	lines=[]
	while foundTemplate and i<len(raw_lines) and raw_lines[i][0]!="#":
		lines.append(raw_lines[i])
		i+=1
	if len(lines)==0:
		print(f"No text found for '{name}' template.  Using generated template.  Edit and save before continuing.")
		subprocess.call(('open', fileName))
		if not confirm("Accept the new template? "):
			if confirm("Save data beforfe exiting? "):
				finish()
			exit()
		return getTemplate(fileName, name)
	return "".join(lines)
	
######################################
# fill out student grade information using a template to format it
def processTemplate(student, assignment, name, fileName="feedback_template.txt"):
	global params
	fileName=status['dataDir'] + fileName
	
	def processUserDefinedKeywords(templateText, fileName):
		userDefiendKeywords=getTemplate(fileName, name="user defined variables")
		for line in userDefiendKeywords.split("\n"):
			if "=" in line:
				templateText=templateText.replace(line.split("=")[0],line.split("=")[1])
		return templateText
	templateText=getTemplate(fileName, name)
	if student != None:
		# preprocess conditional keywords	
		if student.numberOfReviewsGivenOnAssignment(assignment.id)==0:
			templateText=templateText.replace("{comment on review}","{comment on review: no reviews complete}")
		elif student.grades[assignment.id]['review']>90:
			templateText=templateText.replace("{comment on review}","{comment on review: high grade}")
		elif student.grades[assignment.id]['review']<=70:
			templateText=templateText.replace("{comment on review}","{comment on review: low grade}")
		else:
			templateText=templateText.replace("\n{comment on review}","")
			templateText=templateText.replace("{comment on review}","")
		if assignment.id in student.grades and student.points[assignment.id]['total']==student.points[assignment.id]['curvedTotal']:
			templateText=templateText.replace("{comment if grades are curved}","")
		templateText=processUserDefinedKeywords(templateText, fileName)
		template_lines=templateText.split("\n")
		processed_lines=[]
		cids=assignment.criteria_ids()
		# fill in all predefined substitutions
		if assignment.id not in student.creations:
			return None
		for line in template_lines:
			if "by_criteria" in line or "by criteria" in line:
				#xxx for cid in student.pointsByCriteria[assignment.id]: #trying to fix bug Hilary found
				for cid in assignment.criteria_ids(): 
					tempLine=""
					try:
						if cid in student.deviationByAssignment[assignment.id]:
							if  student.deviationByAssignment[assignment.id][cid] > 0.05:
								tempLine=line.replace("{review feedback by criteria}","{review feedback by criteria: higher scores given}")
							elif student.deviationByAssignment[assignment.id][cid] < -0.05:
								tempLine=line.replace("{review feedback by criteria}","{review feedback by criteria: lower scores given}")
							else:
								tempLine=line.replace("{review feedback by criteria}", "{review feedback by criteria: similar scores given}")
						tempLine=processUserDefinedKeywords(tempLine, fileName)
						points=0
						if cid in student.pointsByCriteria[assignment.id]:
							if student.pointsByCriteria[assignment.id][cid]!='':
								points=round(student.pointsByCriteria[assignment.id][cid] * assignment.criteria_points(cid)/ params.pointsForCid(cid, assignment),2)
						processed_lines+=tempLine.format(points_by_criteria=points, description_by_criteria=criteriaDescription[cid], keywordCreation="regrade", keywordReview="recalculate", review_rms_by_criteria=round(student.rmsByAssignment[assignment.id][cid],1), absolute_value_of_deviation=round(abs(student.deviationByAssignment[assignment.id][cid]),1))	+"\n"
					except:
						points=0
						pass
			else:
				if assignment.id in student.grades:
					processed_lines+=line.format(keywordCreation="regrade", keywordReview="recalculate", creationGrade=round(student.grades[assignment.id]['creation']), reviewGrade=round(student.grades[assignment.id]['review']), rawGrade=round(student.grades[assignment.id]['total']), curvedGrade=round(student.grades[assignment.id]['curvedTotal']),solutionsUrl=assignment.solutionsUrl, assignmentName=assignment.name)+"\n"
				else:
					processed_lines+=line.format(keywordCreation="regrade", keywordReview="recalculate", creationGrade="--", reviewGrade="--", rawGrade="--", curvedGrade="--",solutionsUrl=assignment.solutionsUrl, assignmentName=assignment.name)+"\n"				
	else:
		templateText=templateText.replace("{comment on review}","{comment on review: no reviews complete}")
		template_lines=templateText.split("\n")
		processed_lines=[]
		for line in template_lines:
			processed_lines+=line.format(keywordCreation="regrade", keywordReview="recalculate",solutionsUrl=assignment.solutionsUrl, assignmentName=assignment.name)+"\n"
	returnVal="".join(processed_lines)
	return returnVal


######################################
# Go through all submissions for an assignment. If the assignment was created by
# a student in the list of students given, determine a grade for the submission
# based on a weighted average of peer reviews, or using the instructors grade if it
# was graded by the instructor.	 Then look through all the reviews the students in the
# given list of students performed on this assignment and computer a grade for their
# peer reviews based on a weighted average of the deviation from other reviewers.
# finally combine these two grades to get a total grade, and record all three grades
# into the student object, along with comments that can be shared with the student
# explaining the grade		
def gradeStudent(assignment, student, reviewScoreGrading="default"):
	global params
	missingSubmission=False
	if reviewScoreGrading=="default":
		reviewScoreGrading=assignment.reviewScoreMethod
	# get a list of the criteria ids assessed on this assignment
	#calculate creation grades
	curveFunc=eval('lambda x:' + assignment.curve)
	student.gradingExplanation="Creation grade information for " +str(assignment.name) +"\n\n"
	for review in student.reviewsReceived:
		if review.review_type == "grading" and review.assignment_id == assignment.id:
			student.assignmentsGradedByInstructor[assignment.id]=True
			student.gradingExplanation+="This submission was graded by the instructor.\n"
	creationGrade=0
	creationWasReviewed=False
	for cid in assignment.criteria_ids():
		total, numberCount, weightCount = 0, 0, 0
		student.gradingExplanation+=str(criteriaDescription[cid]) + ":\n"
		gradingExplanationLine=""
		multiplier=params.pointsForCid(cid, assignment)
		for review in student.reviewsReceived:
			if review.assignment_id == assignment.id:
				weight=0
				creationWasReviewed=True
				role=""
				gradingExplanationLine=""
				if (review.reviewer_id in studentsById):
					reviewer=studentsById[review.reviewer_id]
					role=reviewer.role
				if review.review_type == "peer_review" and not (assignment.id in student.assignmentsGradedByInstructor):
					if role == 'grader':
						weight=params.gradingPowerForGraders
						gradingExplanationLine="Review [G"+ str(review.reviewer_id) +"_" + str(cid) +"] "
					elif role== 'student':
						#weight=studentsById[review.reviewer_id].getGradingPower(cid); 
						try:
							if assignment.id in reviewer.adjustmentsByAssignment:
								weight=reviewer.adjustmentsByAssignment[assignment.id][cid].gradingPower()
							else:
								weight=reviewer.adjustments[cid].gradingPower()
						except KeyError:
							weight=1 
						gradingExplanationLine="Review [P"+ str(review.reviewer_id)+"_" + str(cid) +"] "
				elif review.review_type == "grading":
					gradingExplanationLine="Review [I"+ str(review.reviewer_id)+"_" + str(cid) +"] "
					weight=params.gradingPowerForInstructors
					role='instructor'
				if cid in review.scores:
					try:
						reviewer=studentsById[review.reviewer_id]
						compensation=reviewer.adjustmentsByAssignment[assignment.id][cid].compensation*params.compensationFactor
						compensation=min(compensation, params.maxCompensationFraction* multiplier)
						compensation=max(compensation, -params.maxCompensationFraction* multiplier)
					except Exception:
						compensation=0	
					if not assignment.id in student.reviewData:
						student.reviewData[assignment.id]=dict()
					if not cid in student.reviewData[assignment.id]:
						student.reviewData[assignment.id][cid]=[]	
					newData={'points': review.scores[cid], 'compensation': compensation, 'weight': weight, 'reviewerID': review.reviewer_id, 'description': criteriaDescription[cid], 'reviewerRole': role}
					replacedData=False
					for i,itm in enumerate(student.reviewData[assignment.id][cid]):
						if itm['reviewerID']==review.reviewer_id:
							replacedData=True
							student.reviewData[assignment.id][cid][i]=newData
					if not replacedData:
						student.reviewData[assignment.id][cid].append(newData)
					gradingExplanationLine+=" Grade of {:.2f} with an adjustment for this grader of {:+.2f} and a relative grading weight of {:.2f}".format(review.scores[cid], compensation, weight)
					if not (str(review.reviewer_id)+"_" + str(cid)) in student.gradingExplanation:
						student.gradingExplanation += "    "  + gradingExplanationLine + "\n"
					total+=max(0,min((review.scores[cid] + compensation)*weight, assignment.criteria_points(cid)*weight)) # don't allow the compensation to result in a score above 100% or below 0%%
					weightCount+=weight
					numberCount+=1
		if not assignment.id in student.pointsByCriteria:
			student.pointsByCriteria[assignment.id]=dict()		
		if (weightCount>0):
			creationGrade+=multiplier*total/(weightCount*assignment.criteria_points(cid))
			student.pointsByCriteria[assignment.id][cid]=multiplier*total/(weightCount*assignment.criteria_points(cid))
		else:
			student.pointsByCriteria[assignment.id][cid]=""
	if (not creationWasReviewed) or weightCount==0:
		#If student had no reviews
		if not assignment.id in student.creations:
			creationGrade=0
			student.gradingExplanation+="No submission received"
			print("No submission for",student.name,"on assignment",assignment.name, "assigning grade of", creationGrade)
			missingSubmission=True
		else:
			if student.creations[assignment.id].submitted_at != None:
				creationGrade=100 # Change this
				student.gradingExplanation+=""#"This submission was not reviewed.  Placeholder grade of " + str(creationGrade) + " assigned\n"
				print("No reviews of",student.name,"on assignment",assignment.name, "assigning placeholder grade of", creationGrade)	
	if reviewScoreGrading.lower()=="calibrated grading":
		#calculate review grades
		tempDelta=dict()
		tempDelta2=dict()
		tempWeight=dict()
		compsOnThisAssignment=[student.comparisons[key] for key in student.comparisons if student.comparisons[key].assignment_id == assignment.id]
		for comp in compsOnThisAssignment:
			otherReview=reviewsById[comp.reviewIDComparedTo]
			thisGivenReview=reviewsById[comp.reviewID]			
			for cid in comp.weight:
				adjustedData=comp.adjustedData(cid, degraded=False)
				if cid not in tempWeight:
					tempDelta[cid]=adjustedData['delta']*adjustedData['weight']
					tempDelta2[cid]=adjustedData['delta2']*adjustedData['weight']
					tempWeight[cid]=adjustedData['weight']
				else:
					tempDelta[cid]+=adjustedData['delta']*adjustedData['weight']
					tempDelta2[cid]+=adjustedData['delta2']*adjustedData['weight']
					tempWeight[cid]+=adjustedData['weight']
		if assignment.id not in student.relativeRmsByAssignment or student.relativeRmsByAssignment[assignment.id]=={}: # i.e. if we haven't already graded this students reviews
			student.rmsByAssignment[assignment.id]=dict()
			student.deviationByAssignment[assignment.id]=dict()
			student.relativeRmsByAssignment[assignment.id]=dict()
			student.weightsByAssignment[assignment.id]=dict()
			if student.reviewGradeExplanation == None:
				student.reviewGradeExplanation=""
				#print(f"setting up reviewGradeExplanation for {student.name} ")
			errorMessage=None
			for cid in [cid for cid in tempDelta if cid!=0]: #iterate through all cids in temDelta except 0
				if tempWeight[cid]!=0:
					student.reviewGradeExplanation+=" for '" + str(criteriaDescription[cid]) +"'\n"
					student.rmsByAssignment[assignment.id][cid]=math.sqrt(tempDelta2[cid]/tempWeight[cid])
					student.deviationByAssignment[assignment.id][cid]=tempDelta[cid]/tempWeight[cid]
					student.relativeRmsByAssignment[assignment.id][cid]=math.sqrt(tempDelta2[cid]/tempWeight[cid]) / assignment.criteria_points(cid)
					student.weightsByAssignment[assignment.id][cid]=tempWeight[cid]
				else:
					#print(f"{student.name}")
					#print(f"{compsOnThisAssignment=}")
					#print(f"{tempDelta=}")
					#print(f"{tempWeight=}")
					if not missingSubmission:
						errorMessage=(f"Unable to record review grade for {student.name} - perhaps no reviews to compare it to?")
					#confirm("proceed?")
					student.rmsByAssignment[assignment.id][cid]=0
					student.deviationByAssignment[assignment.id][cid]=0
					student.relativeRmsByAssignment[assignment.id][cid]=0
					student.weightsByAssignment[assignment.id][cid]=0
			if errorMessage!=None:
				print(errorMessage)
			delta2=weight=0
			for cid in [cid for cid in tempWeight if cid!=0]:
				delta2+=(student.relativeRmsByAssignment[assignment.id][cid]**2)*tempWeight[cid]
				weight+=tempWeight[cid]
				if weight>0:
					rms=(delta2/weight)**0.5
					student.rmsByAssignment[assignment.id][0]=rms*assignment.criteria_points(0)
					student.relativeRmsByAssignment[assignment.id][0]=rms
					student.weightsByAssignment[assignment.id][0]=tempWeight[0]
				else:
					rms=2
					student.rmsByAssignment[assignment.id][0]=None
					student.relativeRmsByAssignment[assignment.id][0]=None
					student.weightsByAssignment[assignment.id][0]=0	
		if 0 in student.relativeRmsByAssignment[assignment.id]:
			rms=student.relativeRmsByAssignment[assignment.id][0]
		else:
			if not missingSubmission:
				print("Unable to get rms for "+ student.name)
			rms=2
		if rms != None:
			reviewGradeFunc= eval('lambda x:' + assignment.reviewCurve.replace('rms','x'))
			reviewGrade=student.amountReviewed(assignment) * reviewGradeFunc(rms)
		else:
			reviewGrade=0
		totalGrade=creationGrade * params.weightingOfCreation + reviewGrade * params.weightingOfReviews
	elif reviewScoreGrading.lower()=="percent completed":
		reviewGrade=student.amountReviewed(assignment) *100
		totalGrade=creationGrade * params.weightingOfCreation + reviewGrade * params.weightingOfReviews
	elif reviewScoreGrading.lower()=="ignore":
		reviewGrade=creationGrade
		totalGrade=creationGrade
	elif reviewScoreGrading.lower()=="keep":
		reviewGrade=student.grades[assignment.id]['review']
		totalGrade=creationGrade * params.weightingOfCreation + reviewGrade * params.weightingOfReviews
	else:
		print("Unknown scorign method '" + reviewScoreGrading + "'.  Use assignment.setReviewScoringMethod() to change")
		exit()	
	#adjust the points from a scale of 100 down to the number of points for the assingmnet
	digits=int(2-math.log10(assignment.points_possible))
	if reviewScoreGrading.lower()=="ignore":
		creationPoints=round(creationGrade*assignment.points_possible/100.0 ,digits)
	else:
		creationPoints=round(creationGrade*assignment.points_possible/100.0*  params.weightingOfCreation ,digits)
	reviewPoints=round(reviewGrade*assignment.points_possible/100.0 * params.weightingOfReviews ,digits)
	if (digits ==0):
		creationPoints=int(creationPoints)
		reviewPoints=int(reviewPoints)
	totalPoints=creationPoints + reviewPoints
	curvedTotalPoints=curveFunc(totalPoints)
	if not assignment.id in student.creations:
		curvedTotalPoints=0 # no submission
	if reviewScoreGrading=="ignore":
		
		student.grades[assignment.id]={'creation': creationGrade, 'review':  None, 'total' :totalGrade, 'curvedTotal': 100.0*curvedTotalPoints/assignment.points_possible}
		student.points[assignment.id]={'creation': creationPoints, 'review':  None, 'total' :totalPoints, 'curvedTotal': curvedTotalPoints}	
	else:
		student.grades[assignment.id]={'creation': creationGrade, 'review':  reviewGrade, 'total' :totalGrade, 'curvedTotal':  100.0*curvedTotalPoints/assignment.points_possible}
		student.points[assignment.id]={'creation': creationPoints, 'review':  reviewPoints, 'total' :totalPoints, 'curvedTotal': curvedTotalPoints}
	percentileRanking=gradingPowerRanking(student, percentile=True)	
	#make a summary of their points

	if reviewScoreGrading.lower()=="ignore":
		templateName="general feedback ignoring reviews"
	elif reviewScoreGrading.lower()=="calibrated grading":
		templateName="general feedback with calibrated review grading"
	if (assignment.id in student.regrade):
		if (student.regrade[assignment.id]=="Started"):
			if (not assignment.id in student.regradeComments or len(student.regradeComments[assignment.id])==0):
				print("using template to craft regrade comments")
				student.regradeComments[assignment.id]=processTemplate(student,assignment,name="regrade comments")
			else:
				print("not using template to craft regrade comments")
	else:			
		student.comments[assignment.id]=processTemplate(student,assignment,name=templateName)
	if not assignment.id in student.creations:
		student.gradingExplanation+="No submission received"
		student.comments[assignment.id]="No submission received"
	student.recordAdjustments(assignment)


######################################
# Get a review grade based only on calibrations that the instructor graded
def reviewGradeOnCalibrations(assignment, student):
	delta2=0
	tempDelta=dict()
	tempWeight=dict()
	numberOfComparisons=0
	if not assignment.id in student.grades:
		gradeStudent(assignment,student)
	oldReviewGrade=student.grades[assignment.id]['review'] 
	try:
		student.calibrationGradeExplanation
	except Exception:
		student.calibrationGradeExplanation=dict()
	#consider reviews in common with the instructor
	#student.calibrationGradeExplanation[assignment.id]="On peer reviews that were ALSO graded by the instructor, compared to the instructor the scores you gave out on average were:\n"
	for key, thisGivenReview in student.reviewsGiven.items():
		blankCreation=len([c for c in creations if c.id == key and c.missing])>0	
		if thisGivenReview.assignment_id == assignment.id and not blankCreation:
			for otherReview in reviewsByCreationId[thisGivenReview.submission_id].values():
				if otherReview.review_type == "grading":
					totalCriteriaPoints=0
					numberOfCriteria=0
					for cid in thisGivenReview.scores:
						totalCriteriaPoints+=assignment.criteria_points(cid)
						numberOfCriteria+=1
						if cid in tempDelta:
							tempDelta[cid]+=thisGivenReview.scores[cid] - otherReview.scores[cid] 
						else:
							tempDelta[cid]=thisGivenReview.scores[cid] - otherReview.scores[cid] 		
						tempWeight[cid]=1						
						delta2+=((thisGivenReview.scores[cid] - otherReview.scores[cid] )/ assignment.criteria_points(cid))**2
						numberOfComparisons+=1 
	if numberOfComparisons!=0:
		averagePointsPerCriteria=totalCriteriaPoints/numberOfCriteria
		rms=(delta2/numberOfComparisons)**0.5
		student.relativeRmsByAssignment[assignment.id][0]=rms # this is new...untested.  Can delete if it causes problems, it is just for updating records that may not be used.
	else:
		print(student.name + " did not grade any calibration assignments on " + assignment.name)
		return
	reviewGradeFunc= eval('lambda x:' + assignment.reviewCurve.replace('rms','x'))
	reviewGrade=reviewGradeFunc(rms)
	student.calibrationGradeExplanation[assignment.id]="On peer reviews that were ALSO graded by me we differed on (rms) average by %.2f points per category, resulting in a regaded review score of %.f\n"%(rms*averagePointsPerCriteria,reviewGrade)		
	curveFunc=eval('lambda x:' + assignment.curve)
	totalGradeDelta= round(reviewGrade-oldReviewGrade)
	totalPointsDelta= round(totalGradeDelta * params.weightingOfReviews*assignment.points_possible/100.0)	
	if not assignment.id in student.regradeComments:
		student.regradeComments[assignment.id]= student.calibrationGradeExplanation[assignment.id]
	else:
		student.regradeComments[assignment.id]+="  After regrading your creation, I regraded your reviews.  " + student.calibrationGradeExplanation[assignment.id]
	useReducedScore=False
	if (totalPointsDelta) < 0:
		print(f"\nRecalcualtion of {student.name}'s review score resulted in a lower grade:")
		print(f'    review scores went from {round(student.grades[assignment.id]["review"])} -> {reviewGrade}')
		print(f'    curved score went from {student.grades[assignment.id]["curvedTotal"]} -> {round(curveFunc(student.grades[assignment.id]["total"]))}')
		useReducedScore=confirm("Reduce score for "+student.name+" by " + str(-totalPointsDelta) + " points? ")
		if not useReducedScore:
			student.regradeComments[assignment.id]+="This would actually lower your review grade, but I chose to leave it as is.  "
	if (totalPointsDelta) > 0 or useReducedScore:
		student.grades[assignment.id]['review']=reviewGrade
		student.points[assignment.id]['review']=round(reviewGrade * assignment.points_possible/100.0 * params.weightingOfReviews)
		student.grades[assignment.id]['total']=student.grades[assignment.id]['review'] * params.weightingOfReviews + student.grades[assignment.id]['creation'] * params.weightingOfCreation
		student.points[assignment.id]['total']=round((student.grades[assignment.id]['review'] * params.weightingOfReviews + student.grades[assignment.id]['creation'] * params.weightingOfCreation)*assignment.points_possible/100.0)
		student.grades[assignment.id]['curvedTotal']=curveFunc(student.grades[assignment.id]['total'])
		student.points[assignment.id]['curvedTotal']=round(curveFunc(student.grades[assignment.id]['total'])*assignment.points_possible/100.0)
		if (totalPointsDelta) > 0:
			student.regradeComments[assignment.id]+="This increased your review grade by " + str(totalGradeDelta) + " percent, increasing your total (curved) score for the assignment to " + str(student.points[assignment.id]['curvedTotal']) + ".  "
		else:
			student.regradeComments[assignment.id]+="This decreased your review grade by " + str(-totalGradeDelta) + " percent, decreasing your total (curved) score for the assignment to " + str(student.points[assignment.id]['curvedTotal'])+ ".  "
	elif totalPointsDelta==0:
		student.regradeComments[assignment.id]+="This did not change your review grade."
	return student.points[assignment.id]['curvedTotal']

######################################
# find submissions that need to be regraded as based on a keyword in the comments
def regrade(assignmentList="all", studentsToGrade="All", recalibrate=False):
	global status, activeAssignment
	if not status['initialized']:
		print("Error: You must first run 'initialize()' before calling 'regrade'")
		return
	if assignmentList==None or (isinstance(assignmentList, str) and assignmentList.lower()=="all"):
		assignmentList=list(set([g for g in graded_assignments.values() if g.graded and not g.regradesCompleted]))
	assignmentList=makeList(assignmentList)
	if len(assignmentList)==0:
		print("No assignments  to regrade")
		return
	assignmentList=makeList(assignmentList)
	assignmentList.sort(key = lambda x : x.name)
	for assignment in assignmentList:
		getStudentWork(assignment) # does this slow things down too much?
		unresolvedRegrades=False
		print("\nRegrading " + assignment.name + "...")				
		studentsNeedingRegrade=dict()
		#make list of students needing a regrade
		if str(studentsToGrade)==studentsToGrade and studentsToGrade.lower()=="all":
			for i,student in enumerate(makeList(students)):
				if assignment.id not in student.regrade or (student.regrade[assignment.id]!="Forget" and student.regrade[assignment.id]!="Done"):
					for key in student.creations:
						c = student.creations[key]
						#printLine("Checking for a regrade request from " + student.name + " " + str(i+1)+"/"+str(len(makeList(students))),newLine=False) 
						printLeftRight("Checking for a regrade request from " + student.name ,str(i+1)+"/"+str(len(makeList(students))), end="")
						try:
							if c.assignment_id == assignment.id:
								comments=c.edit().submission_comments
								for comment in comments:
									if comment['author']['id'] not in studentsById and "I've regraded your work" in comment['comment']:
										print(student.name + " had a regrade processed alerady")
									elif comment['author']['id'] == c.author_id and  (comment['comment'].lower().count(keywordCreation) ):
										if not (assignment.id in student.regrade): 
											if c.edit().id not in studentsNeedingRegrade:
												studentsNeedingRegrade[c.edit().id]=student
												printLine(student.name + " has a new regrade request pending")										
									if comment['author']['id'] == c.author_id and  ( comment['comment'].lower().count(keywordReview) ):
										if not (assignment.id in student.regrade): 
											if c.edit().id not in studentsNeedingRegrade:
												studentsNeedingRegrade[c.edit().id]=student
												printLine(student.name + " has a new recalculation request pending")										
						except KeyboardInterrupt:
							exit()
			printLine("",newLine=False)
		else:
			for student in makeList(studentsToGrade):
				print("Looking for a regrade request from " + str(student.name))
				for key in student.creations:
					c = student.creations[key]
					comments=c.edit().submission_comments
					if c.assignment_id == assignment.id:
						for comment in comments:
							if comment['author']['id'] == c.author_id and (comment['comment'].lower().count(keywordCreation) or comment['comment'].lower().count(keywordReview) ):
								if not (assignment.id in student.regrade):
									studentsNeedingRegrade[c.edit().id]=student									
		#process list of students needing a regrade
		for i, student_key in enumerate(studentsNeedingRegrade):
			student=studentsNeedingRegrade[student_key]
			for key in student.creations:
				c = student.creations[key]
				if c.assignment_id == assignment.id:
					comments=[com['comment'] for com in c.edit().submission_comments if com['author']['id'] == student.id]					
					#print("regrade requested by " + student.name + "for assignment at: ")
					previewUrl=c.edit().preview_url.replace("preview=1&","")
					previewBaseUrl=previewUrl.split("?")[0]
					speedGraderURL=previewBaseUrl.replace("assignments/","gradebook/speed_grader?assignment_id=").replace("/submissions/", "&student_id=")

					
					printLeftRight("\n---------- " + student.name + " (Sec "+ str(int(student.sectionName[-2:])) +") says: ---------- " ,str(i+1)+"/" +str(len(studentsNeedingRegrade)))
					print("\n" + Fore.GREEN +  Style.BRIGHT +"\n\n".join(comments)+Style.RESET_ALL + "\n")
					
					alreadyGradedByProfessor=student.id in [pr.author_id for pr in professorsReviews[assignment.id]]
					if alreadyGradedByProfessor:
						print(Fore.BLUE +  Style.BRIGHT  +"Already graded by professor"+Style.RESET_ALL)
					else:
						webbrowser.open(speedGraderURL)
					val="unknwon"
					default="unknown"
					while not val in ["i","f","v","r","c", "p","cp", "pc", "e"]:
						if " ".join(comments).lower().count(keywordReview) and not " ".join(comments).lower().count(keywordCreation):
							print("Student indicated they want the reviews recalculated (e) or (p) to evaluate peer review scores")
							default="p"
						elif " ".join(comments).lower().count(keywordCreation) and not " ".join(comments).lower().count(keywordReview):
							print("Student indicated they want the creations regraded (e) or (c) to evaluate creation score")
							default="c"
						else:
							print("Student wants both reviews and creations reviewed (e) or (cp) to evaluate both")
							default="cp"
						if val!="v":
							if not alreadyGradedByProfessor:
								val=input("\n\t(i) to ignore this request for now\n\t(f) to forget it forever\n\t(r) to get a grading report\n\t(c) to rescore creation (only)\n\t(p) to recalculate peer review score (only)\n\t(cp) to rescore creation and review\n")
							else:
								val=input("\n\t(i) to ignore this request for now\n\t(f) to forget it forever\n\t(r) to get a grading report\n\t(v) to view student's work in a web browser\n\t(c) to rescore creation (only)\n\t(p) to recalculate peer review score (only)\n\t(cp) to evaluate creation and review\n")						
						else:
							val=input("enter choice: ")
						if val=='e':
							val=default
						if val=='i':
							unresolvedRegrades=True
							if  assignment.id in student.regrade:
								student.regrade.pop(assignment.id)
						if val=='f':
							student.regrade[assignment.id]="Forget"
						if val=="v":
							val="unknwon"
							print("Enter any regrade info and comments into the web browser")
							webbrowser.open(speedGraderURL)
						if val=="r":
							val="unknwon"
							student.pointsOnAssignment(assignment)
						if val=="cp" or val=="pc":
							student.regrade[assignment.id]="Started creation and review"
						if val=="c":
							student.regrade[assignment.id]="Started creation"
						if val=="p":
							student.regrade[assignment.id]="Started review"
		print("\n")
		msg=assignment.name +  " regraded with the following point values:\n"
		for cid in assignment.criteria_ids():
			msg+= "\t(" +str(params.pointsForCid(cid,assignment ))+ ") " + criteriaDescription[cid] + "\n"
		log(msg,False)
		#regenerate the dictionary with only students who need to be processed
		studentsNeedingCreationRegradeList=[s for s in students if assignment.id in s.regrade and "creation" in s.regrade[assignment.id]]
		studentsNeedingReviewRegradeList=[s for s in students if assignment.id in s.regrade  and "review" in s.regrade[assignment.id]]
		studentsNeedingCreationRegrade=dict()
		studentsNeedingReviewRegrade=dict()
		for rs in studentsNeedingCreationRegradeList:
			studentsNeedingCreationRegrade[rs.id]=rs
		for rs in studentsNeedingReviewRegradeList:
			studentsNeedingReviewRegrade[rs.id]=rs
		studentsNeedingRegrade=studentsNeedingCreationRegrade.copy()
		studentsNeedingRegrade.update(studentsNeedingReviewRegrade)
		if len(studentsNeedingRegrade)>0:
			print("Getting updated submissions")			
			getStudentWork(assignment)
			if (recalibrate):
				print("Before posting the regrade results, lets recalibrate the graders")
				calibrate()
			print("OK, now lets go through each regraded student to post their scores and comments")
			originalPoints=dict()
			for student_key in studentsNeedingRegrade:
				try:
					originalPoints[student_key]=studentsNeedingRegrade[student_key].grades[assignment.id]
				except KeyError:
					print("unable to get original grade for " + studentsNeedingRegrade[student_key].name)
					originalPoints[student_key]=0				
			grade(assignment, studentsToGrade=list(studentsNeedingCreationRegrade.values()), reviewScoreGrading='keep')			
			for student_key in studentsNeedingRegrade:
				student=studentsNeedingRegrade[student_key]
				#get the grade from saved data for the student
				originalCurvedTotalPoints=originalPoints[student_key]['curvedTotal'] 
				#if possible, read the grade from canvas
				submission=[c for c in creations if c.assignment_id == assignment.id and c.author_id == student.id]
				if len(submission)>0:
					submission=submission[0]
					canvasGrade=float(submission.grade)
					if (canvasGrade!=originalCurvedTotalPoints):
						print(f"Warning: Canvas grade of {canvasGrade} does not match what is in memory {originalCurvedTotalPoints}, but regardless the grade on canvas is about to be overwritten with a new grade")
					originalCurvedTotalPoints=canvasGrade
					
				if student in studentsNeedingReviewRegradeList:
					reviewGradeOnCalibrations(assignment,student)
				digits=int(2-math.log10(assignment.points_possible))
				creationGrade=student.grades[assignment.id]['creation']
				reviewGrade=student.grades[assignment.id]['review']
				totalPoints=student.points[assignment.id]['total'] # xxx to see if a grade should be curved compare grades and points
				curvedTotalPoints=student.points[assignment.id]['curvedTotal']
				totalScoringSummaryString=("You earned %." + str(digits) +"f%% for your submission and %." + str(digits) +"f%% for your reviews.   When combined this gives you %." + str(digits) +"f%%.") % (creationGrade,  reviewGrade, totalPoints ) 
				if (curvedTotalPoints!=totalPoints):
					totalScoringSummaryString+=(("  When curved this gives a final regraded score of %." + str(digits) +"f.") % (curvedTotalPoints) )
				if assignment.id in student.regradeComments:
					student.regradeComments[assignment.id] += totalScoringSummaryString
				else:
					student.regradeComments[assignment.id] = totalScoringSummaryString
				if assignment.id in student.regrade and student.regrade[assignment.id]!="Forget" and student.regrade[assignment.id]!="Done":
					scoreDelta=curvedTotalPoints-originalCurvedTotalPoints					
					printLine("\nRegrade comments for " + student.name, newLine=False)
					print(student.regradeComments[assignment.id])
					if scoreDelta<0:
						print(f"\n{Fore.RED}{Style.BRIGHT}Score will go from {originalCurvedTotalPoints} to {curvedTotalPoints}, a loss of {-scoreDelta} points{Style.RESET_ALL}")
					elif scoreDelta>0:
						print(f"\nScore will go from {originalCurvedTotalPoints} to {curvedTotalPoints}, a gain of {scoreDelta} points")
					else:
						print(f"\nScore will not change")
					if confirm("Ok to post?"):
						postGrades(assignment, listOfStudents=[student], useRegradeComments=True)
						student.regrade[assignment.id]="Done"
						print("Posted regrade for " + student.name)
					else:
						print("Not posting anything for " + student.name)
						print("If you entered the score and comments manually, it should be marked as complete.")
						if confirm("Mark " + student.name + "'s regrade as complete?"):
							student.regrade[assignment.id]="Done"
				else:
					print("Not posting anything for " + student.name)
				printLine(line=True)
		else:
			print("There are no pending regrade requests for " + assignment.name)
		printLine()
		if unresolvedRegrades:
			assignment.regradesCompleted=False
		else:
			if confirm("Shall we finalize " + assignment.name + " and stop checking it for regrade requests?"):
				assignment.regradesCompleted=True
			else:
				assignment.regradesCompleted=False
		
		status["regraded"]=True
		assignment.regraded=True		
	dataToSave['students']=True
	dataToSave['assignments']=True
		
######################################
# For the assignment given, post the total grade on canvas and post the associated
# comments.	 The optional arguments allow you to suppress posting comments or the grades
def postGrades(assignment, postGrades=True, postComments=True, listOfStudents='all', useRegradeComments=False):
	global status
	if not status['initialized']:
		print("Error: You must first run 'initialize()' before calling 'postGrades'")
		return
	if not status['gotStudentsWork']:
		print("Error: You must first run 'getStudentWork()' before calling 'postGrades'")
		return	
	if not status['graded']:
		if not confirm("You haven't yet called grade() but you are calling postGrades()\nyou will be posting previously saved grades, and may get an error", False):
			return
	if (listOfStudents=='all'):
		listOfStudents=[s for s in students if s.role=='student']
	for student in listOfStudents:
		if assignment.id in student.creations:
			creation=student.creations[assignment.id]
			printLine("posting for " + student.name, newLine=False)
			if postGrades:
				creation.edit(submission={'posted_grade':student.points[assignment.id]['curvedTotal']})
			if postComments:
				try:
					theComment=additionalGradingComment + "\n\n"
				except:
					theComment=""
				if useRegradeComments and assignment.id in student.regradeComments:
					theComment=student.regradeComments[assignment.id]
				elif not useRegradeComments:
					theComment=student.comments[assignment.id]
				creation.edit(comment={'text_comment':theComment})			
		else:
			printLine("No creation to post for " + student.name, newLine=False)
	printLine()
	assignment.gradesPosted=True	
	dataToSave['assignments']=True
	log("Grades for " +assignment.name+ " posted")
	status["posted"]=True

######################################
# Read a CSV file with student names, grades, and comments and upload that data for the
# assignment from which the creations were taken
def postFromCSV(fileName=None, thisAssignment=None):
	global course, creations
	print("getting list of assignments...")
	if thisAssignment==None:
		assignments = course.get_assignments()
		for (i,assignment) in	enumerate(assignments):
			print(str(i+1)+")",assignment.name)
		val=int(input("Choose the assignment index: "))-1
		thisAssignment=assignments[val]
	elif thisAssignment.lower()=='last':
		thisAssignment=graded_assignments['last']
	print("accessing "+thisAssignment.name+"...")
	submissions=thisAssignment.get_submissions()
	#get student names, scores and comments from CSV file
	csvData=readCSV(fileName)
	nameCol, gradeCol, commentCol= -1 ,-1 ,-1 
	for (i,col) in	enumerate(csvData[0]):
		if col.strip().lower() == "name":
			nameCol=i
			print(i+1,col,"<- Name")
		elif col.strip().lower() == "grade" or col.strip().lower() == "adjusted total" or col.strip().lower() == "total":
			gradeCol = i
			print(i+1,col,"<- Grade")
		elif col.strip().lower() == "comment":
			commentCol = i
			print(i+1,col,"<- Comment")
		else:
			print(i+1,col)
	temp=input("Which coulumn number contains the student names? ["+str(nameCol+1)+"] ")	
	if temp!="":
		nameCol=int(temp)-1
	temp=input("Which coulumn number contains the student grades (0 for none)? [" +str(gradeCol+1)+"] ")
	if temp!="":	
		gradeCol=int(temp)-1
	temp=input("Which coulumn number contains the comments (0 for none)? [" +str(commentCol+1)+"] ")
	if temp!="":	
		commentCol=int(temp)-1
	for submission in submissions:
		if submission.user_id in studentsById:
			student=studentsById[submission.user_id]
			for (j, row) in enumerate(csvData):
				try:
					if ((student.name == row[nameCol] or student.sortable_name == row[nameCol])
					 and submission.assignment_id == thisAssignment.id):
						msg="posting "+ student.name + ":\n"
						if gradeCol!=-1:
							submission.edit(submission={'posted_grade':row[gradeCol]})
							msg+="\tscore: " + row[gradeCol] +"\n"
						if commentCol!=-1:
							submission.edit(comment={'text_comment':row[commentCol]})
							msg+="\tcomment: '" + row[commentCol] +"'\n"
						print(msg, end="")
				except Exception:
					status['err']="unable to process test student"
	thisAssignment.gradesPosted=True	
	dataToSave['assignments']=True
	log("Grades for " +thisAssignment.name+ " posted via file'" + fileName + "'")
	status["posted"]=True

######################################
# If the grading parameters were not available in a saved file, prompt the user
# for these.  These parameters are used to define things like the weighting of
# various rubric criteria, and the weighting of the submission score versus the 
# review score.	 The results get saved to a file so they don't need to be 
# reentered everytime the script is run
def getParameters(ignoreFile=False, selectedAssignment="all"):
	global status, criteriaDescription, params
	if ignoreFile:
		params=Parameters()
		params.loadedFromFile=False
	logFile = open(status['dataDir'] +status['prefix'] + 'parameters.log', "a") 	
	headerWritten=False
	for key, assignment in graded_assignments.items():
		if assignment != [] and assignment!=None:
			needInput=False
			try:
				for criteria in assignment.rubric:
					criteriaDescription[criteria['description']]=criteria['description']
					if not criteria['description'] in params.multiplier:
						needInput=True
			except AttributeError:
				print(f"'{graded_assignments[key].name}' does not have a rubric attached")
			if needInput or (selectedAssignment==assignment):
				if not headerWritten:
					logFile.write("----" + str(datetime.now()) + "----\n")
					headerWritten=True
				print("Need to assign criteria weightings for the rubric assigned to " + assignment.name + ": ")
				for criteria in assignment.rubric:
					if not criteria['description'] in params.multiplier: 
						print("\t" + criteria['description'])
					else:
						print("\t" + criteria['description'] + " (" + str(params.multiplier[criteria['description']]) +")")
				print("")
				for criteria in assignment.rubric:
					criteriaDescription[criteria['description']]=criteria['description']
					if not criteria['description'] in params.multiplier or (selectedAssignment==assignment):
						params.multiplier[criteria['description']]=getNum("How many points (out of 100) should\n\t" +criteria['description'] + "\nbe worth? ",limits=[0,100], fileDescriptor=logFile)
						#val=float(input("\nHow many points (out of 100) should\n\t" +criteria['description'] + "\nbe worth? "))
						#params.multiplier[criteria['description']]=val
						#logFile.write(How many points (out of 100) should\n\t" +criteria['description'] + "\nbe worth?: " + str(val))
	if not params.loadedFromFile or ignoreFile:
		weightingOfCreation=getNum("Enter the relative weight of the creation towards the total grade",0.7, fileDescriptor=logFile)
		weightingOfReviews=getNum("Enter the relative weight of the review towards the total grade",0.3, fileDescriptor=logFile)
		total=weightingOfCreation+weightingOfReviews
		params.weightingOfCreation=weightingOfCreation/total
		params.weightingOfReviews=weightingOfReviews/total
		params.numberOfReviews=getNum("How many reviewers should review each creation? (some students will be assigned one more than this number of reviews)",3, fileDescriptor=logFile)	
		#params.peerReviewDurationInDays=getNum("How many days should the students have to complete their peer reviews?",3, fileDescriptor=logFile)
		params.gradingPowerForInstructors=getNum("How many times greater than a student should an instructors grading be weighted?",10, fileDescriptor=logFile)
		params.gradingPowerForGraders=getNum("How many times greater than a student should  student graders grading be weighted?",5, fileDescriptor=logFile)
		params.halfLife=getNum("How many assignments is the half life for grading power calculations?",4, fileDescriptor=logFile)
		params.compensationFactor=getNum("What compensation factor for grader deviations (0-1)?",1,[0,1], fileDescriptor=logFile)
		if (params.compensationFactor>0):
			params.maxCompensationFraction=getNum("What is the max fractional amount of a score that can be compensated (0-1)?",defaultVal=0.2,limits=[0,1], fileDescriptor=logFile)
		else:
			params.maxCompensationFraction=0;
	logFile.close()
	dataToSave['parameters']=True
	status["gotParameters"]=True
	return params

def setPoints(assignment):
	global params
	assignment.setPoints(params.multiplier)
	dataToSave['assignments']=True

######################################
# save data to a log file
def log(msg, display=True, fileName=None):
	if fileName==None:
		#fileName=status['prefix']+"log.txt"
		fileName=status['prefix']+"log.txt"
	theFile=status['dataDir'] + fileName
	if display:
		print(msg, end ="")
	f = open(theFile, "a")
	f.write("----" + str(datetime.now()) + "----\n")
	f.write(msg) 
	f.write("\n\n") 
	f.close()

######################################
# look in the log to see if the searchText esists
def findInLog(searchText, fileName=None):
	if fileName==None:
		#fileName=status['prefix']+"log.txt"
		fileName=status['prefix']+"log.txt"
	theFile=status['dataDir'] + fileName
	try:
		f = open(theFile, "r")
		lines = f.readlines()
		f.close()
	except:
		return False
	print("Previously known peer reviewed assignments: ")
	for line in lines:
		if searchText in line:
			return True
	print("Select an assignment or hit <enter> to refresh the list: ")

######################################
# Export the student grades for the given assignment to a file and optionally print
# them on the screen too.		
def getStatistics(assignment=lastAssignment, text=True, hist=False):
	creationGrade=[]
	reviewGrade=[]
	rawTotal=[]
	curvedTotal=[]
	zeros=[]
	for student in students:
		if assignment.id in student.creations:
			if assignment.id in student.grades and assignment.id in student.points:
				points=student.points[assignment.id]
				grades=student.grades[assignment.id]
				creationGrade.append(grades['creation'])
				reviewGrade.append(grades['review'])
				rawTotal.append(grades['total'])
				curvedTotal.append(points['curvedTotal'])
		else:
			zeros.append(0)
	if len(curvedTotal)==0 or not assignment.graded:
		print("You must grade the assignment before getting statistics")
		return
	if hist:
		#importing required libraries
		from matplotlib import pyplot as plt
		# A dataset of 10 students
		marks = curvedTotal + zeros
		fig, axis = plt.subplots(figsize =(10, 5))
		#axis.hist(marks, bins = [0, 10, 20, 30, 40,50, 60, 70, 80, 90, 100])
		axis.hist(marks, bins = [i*assignment.points_possible/10 for i in range(11)])
		plt.title('Curved grades\n\n',
				  fontweight ="bold")
		# Displaying the graph
		plt.show(block=False)
	if text:
		print("Creation average is %.1f%% with stdev of %.1f" % (np.average(creationGrade),np.std(creationGrade)) )	
		print("Review average is %.1f%% with stdev of %.1f" % (np.average(reviewGrade),np.std(reviewGrade)) )	
		print("Raw total average is %.1f%% with stdev of %.1f" % (np.average(rawTotal),np.std(rawTotal)) )	
		print("Curved average is %.1f with stdev of %.1f" % (np.average(curvedTotal),np.std(curvedTotal)) )	
	assignment.creationAverage=np.average(creationGrade)
	assignment.creationStd=np.std(creationGrade)
	assignment.reviewAverage=np.average(reviewGrade)
	assignment.reviewStd=np.std(reviewGrade)
	assignment.rawAverage=np.average(rawTotal)
	assignment.rawStd=np.std(rawTotal)	
	assignment.curvedAverage=np.average(curvedTotal)
	assignment.curvedStd=np.std(curvedTotal)
	
######################################
# Import the student grades for the given assignment from a file =
# them on the screen too.		
def importGrades(assignment=None, fileName=None, overwrite=False):
	if assignment==None:
		assignment=chooseAssignment()
	if fileName==None and assignment!= None:
		fileName="scores for " + assignment.name + ".csv"
	fileName=status['dataDir'] + fileName
	try:
		csvData=readCSV(fileName)
	except Exception:
		raise Exception("unable to read file '" + fileName +"'")
	nameCol, gradeCol, creationCol, reviewCol, rawCol = -1 ,-1 ,-1 , -1, -1
	for (i,col) in enumerate(csvData[0]):
		if col.strip().lower() == "name":
			nameCol=i
		elif col.strip().lower() == "grade" or col.strip().lower() == "adjusted total" or col.strip().lower() == "total":
			gradeCol = i
		elif col.strip().lower() == "creation":
			creationCol = i
		elif col.strip().lower() == "review":
			reviewCol = i
		elif col.strip().lower() == "raw total":
			rawCol = i
	if nameCol<0 or nameCol<0 or creationCol<0 or reviewCol<0 or rawCol<0:
		raise Exception("Unable to  find all column headers")
		return
	for (j, row) in enumerate(csvData):
		temp=[s for s in students if s.name == row[nameCol]]
		if len(temp)>0:
			student=temp[0]
			grade=row[gradeCol]
			creationScore=row[creationCol]
			reviewScore=row[reviewCol]
			rawScore=row[rawCol]
			if (not assignment.id in student.grades) or overwrite:
				student.grades[assignment.id]=dict()
				student.grades[assignment.id]['creation']=(float(creationScore)/0.7)
				student.grades[assignment.id]['review']=(float(reviewScore)/0.3)
				student.grades[assignment.id]['total']=(float(creationScore)+float(reviewScore))
				student.grades[assignment.id]['curvedTotal']=float(grade)
			if (not assignment.id in student.points) or overwrite:
				student.points[assignment.id]=dict()
				student.points[assignment.id]['creation']=int(creationScore)
				student.points[assignment.id]['review']=int(reviewScore)
				student.points[assignment.id]['total']=int(rawScore)
				student.points[assignment.id]['curvedTotal']=int(grade)

######################################
# Export the student grades for the given assignment to a file and optionally print
# them on the screen too.		
def exportGrades(assignment=None, fileName=None, delimiter=",", display=False, saveToFile=True):
	#fileName = "gradesheet.csv"
	if fileName==None and assignment!= None:
		fileName="scores for " + assignment.name + ".csv"
	fileName=status['dataDir'] + fileName
	header="Name" + delimiter +"Sortable Name" + delimiter + "ID" + delimiter
	if assignment!=None:
		for cid in assignment.criteria_ids():
			try:
				header+='"' + assignment.criteria_descriptions(cid) + '"' + delimiter #"LO" + str(cid) + delimiter
			except Exception:
				header+='"' + cid + '"' + delimiter #"LO" + str(cid) + delimiter
		header+="Creation" + delimiter + "Review" + delimiter + "Raw Total" + delimiter +"Adjusted Total" + delimiter + "Comment" + delimiter + "Submission Grading Explanation" + delimiter +  "Review Grade Explaantion\n" 
	else:
		header+="Grade, Comment\n"
	if saveToFile:
		f = open(fileName, "w")
		f.write(header) 
	if display:
		print(fileName[:-4])
		print(header)
	for (i,student) in enumerate(students):
		if student.role=='student':
			line=(student.name + delimiter + 
				'"' + student.sortable_name + '"' + delimiter + 
				str(student.sis_user_id) + delimiter)
			if assignment!=None:
				if assignment.id in student.points:
					points=student.points[assignment.id]	
					for cid in assignment.criteria_ids():
						if assignment.id in student.pointsByCriteria and cid in student.pointsByCriteria[assignment.id]:
							line+=str(student.pointsByCriteria[assignment.id][cid]) + delimiter
						else:
							line+="" + delimiter
					line+=(str(points['creation']) + delimiter + 
						str(points['review']) + delimiter + 
						str(points['total']) + delimiter + 
						str(points['curvedTotal']) + delimiter + 
						'"' + student.comments[assignment.id] + '"' + delimiter +
						'"' + student.gradingExplanation + '"' + delimiter +
						'"' + student.reviewGradeExplanation + '"')
			else:
				line+= ','
			line+='\n'
			if saveToFile:
				f.write(line)
			if display:
				print(line, end ="")
	if saveToFile:
		f.close()

######################################
# view students that are as graders
def viewGraders():
	listOfGraders=[s for s in students if s.role=='grader']
	if len(listOfGraders) > 0:
		print("\n\nCurrent graders are ")
		for g in listOfGraders:
			print("\t"+g.name)
	else:
		print("The class has no graders.")
	print()
	
######################################
# Select students to be assigned as graders
def assignGraders():
	listOfGraders=[s for s in students if s.role=='grader']
	viewGraders()
	if confirm("is this ok? "):
		#for s in listOfGraders:
		#	s.baseGradingPower=params.gradingPowerForGraders
		dataToSave['students']=True
		return
	for (i,student) in enumerate(students):
		print(str(i+1)+")\t" + student.name)
	val=input("enter numbers of all students you want to be graders separated by commas: ")
	indicesPlusOneOfGraders=val.replace(" ","").split(",")
	for s in students:
		if s.role=='grader':
			s.role='student'
	try:
		for ip in indicesPlusOneOfGraders:
			i=int(ip)-1 # convert from 1-based numbering scheme to zero based scheme
			students[i].role='grader'
	except Exception:
		print("Error with your input.  Try again.")
	assignGraders()

######################################
# Get the grading power ranking
def gradingPowerRanking(theStudent="all",cid=0, percentile=False):
	sortedStudents=sorted(students, key = lambda x : x.getGradingPower(cid), reverse=True) 
	if theStudent=="all":
		print("--Best graders--")
		for (i,student) in enumerate(sortedStudents):
			if student.role=='grader':
				print(str(i+1)+")\t" + student.name + " (grader) %.2f -> %.2f" % (student.getGradingPower(cid),params.gradingPowerForGraders))
			else:
				print(str(i+1)+")\t" + student.name + " %.2f" % student.getGradingPower(cid))
		print("--Worst graders--")
		return
	rank=0	
	for student in sortedStudents:
		rank+=1
		if theStudent.id == student.id:
			break
	if percentile:
		return int(round(100.0*(len(sortedStudents)-rank)/len(sortedStudents),0))
	return rank

######################################
# Get the grading deviation ranking
def gradingDeviationRanking(theStudent="all", cid=0, percentile=False):
	sortedStudents=sorted(students, key = lambda x : x.adjustments[cid].deviation, reverse=True) 
	if theStudent=="all":
		print("--Easiest graders--")
		for (i,student) in enumerate(sortedStudents):
			if student.role == 'student':
				print(str(i+1)+")\t" + student.name + " %.2f" % student.adjustments[cid].deviation)
			elif student.role == 'grader':
				print(str(i+1)+")\t" + student.name + " %.2f  (grader)" % student.adjustments[cid].deviation)
		print("--Hardest graders--")
		return
	rank=0
	for student in sortedStudents:
		rank+=1
		if theStudent.id == student.id:
			break
	if percentile:
		return int(round(100.0*(len(sortedStudents)-rank)/len(sortedStudents),0))
	return rank

######################################
# Send an announcement to the canvas course			
def announce(subject, body, section="all"):
	if section == "all":
		announcement=course.create_discussion_topic(message=body, title=subject, is_announcement=True)
	else:
		announcement=course.create_discussion_topic(message=body, title=subject, is_announcement=True, specific_sections=section)

######################################
# Send a canvas message to a student or list of students.		
def message(theStudents, body, subject='', display=False):
	studentList=makeList(theStudents)
	for student in studentList:
		try:
			canvas.create_conversation(student.id, body=body, subject=subject)
		except Exception:
			print("error messaging " ,student.name, ".  Perhaps the student dropped." )
		if display:
			print("messaging " +  student.name)
			
######################################
# Read a CSV file and return the data as an array
def readCSV(fileName=None):
	fileName=fileName.strip().replace("\\","")
	if fileName==None:	
		fileName = input('Select the CSV file to read: ').strip().replace("\\","") # show an "Open" dialog box and 
	data=[]
	with open(fileName, mode ='r') as file:
		csvFile = csv.reader(file)
		for lines in csvFile:
			data.append(lines)
		pass
	return data

######################################
# Prompt the user for a response and confirm their response before returning it.
def confirm(msg="", requireResponse=False):
	msg=formatWithBoldOptions(msg)
	confirmationResponse=""
	if not requireResponse:
		print(msg)
		confirmationResponse=input("'ok' to accept: " )
		return (confirmationResponse == 'ok')
	while confirmationResponse!='ok':
		response=input(msg)
		confirmationResponse=input("You entered '" + str(response) +"'\n'ok' to accept: " )
	return response


######################################
# Prompt for a number with a default value
def getNum(msg="choose a number", defaultVal=None, limits=None, fileDescriptor=None):
	dafaultString=""
	if defaultVal!=None:
		dafaultString=" [" + str(defaultVal) + "]"
	while True:
		response=input(msg + dafaultString +": ")
		if response=="":
			response=defaultVal
		try:
			val=float(response)
			if limits == None or (val>= limits[0] and val <= limits[1]):
				if fileDescriptor!=None:
					fileDescriptor.write(msg +": " + str(val) + "\n")
				return val
			else:
				print("Your response must be between " + str(limits[0]) + " and " + str(limits[1]))
		except Exception:
			print("Your response must be numeric")			

######################################
# Display text and allow the user to accept it or edit it
def confirmText(msg,prompt="Is the following text ok?"):
	print(prompt +"\n")
	print(msg  +"\n")
	val=input("[a] accept or (e) edit?: ")
	if val=="a" or val=="":
		return msg 
	else:
		fileName="temp.txt"
		f = open(fileName, "w")
		f.write(msg)
		f.close()
		subprocess.call(('open', fileName))	
		input("Edit and save the text file '"+fileName+"' then enter to continue: ")
		f = open(fileName, "r")
		lines = f.readlines()
		f.close()
		print(lines)
		os.remove(fileName)
		msg="".join(lines)
		return confirmText(msg, prompt)

######################################
# select a student by partial name match  
def selectStudentByName(theName):
	options=[s for s in students if s.name.lower().find(theName.lower())>-1]
	if len(options)==0:
		print("Unable to find a matching student")
		return select(students,property="name", requireConfirmation=False)
	elif len(options)==1:
		print(options[0].name)
		return options[0]
	else:
		return select(options,property="name", requireConfirmation=False)
		
######################################
# List all objects in an array and prompt the user to select one.  
# Once they confirm their choice it will be returned
def select(objArray, property=None, prompt="Choose one", requireConfirmation=True):
	for i,obj in enumerate(objArray):
		if property==None:
			print(i , obj)
		else:
			print(i , eval("obj." + property))	
	confirmed=False
	while not confirmed:
		response=input(prompt + ": ")
		selection=int(response)
		if requireConfirmation:
			if property==None:
				response = input("type 'ok' to confirm or choose a new value [" + str(objArray[selection]) + "]: " )
			else:
				response = input("type 'ok' to confirm or choose a new value [" + str(eval("objArray[selection]." + property)) + "]: " )
			confirmed = (response == 'ok')
		else:
			confirmed = True
	return objArray[selection]

######################################
# print groups and membership
def printGroups():
	groupsSets=course.get_group_categories()[0]
	for group in groupsSets.get_groups():
		print (group.name + ":")
		for membership in group.get_memberships():
			member=studentsById[membership.user_id]
			print("\t" + member.name)
		print()
	print("List of all students in a group")
	for group in groupsSets.get_groups():
		for membership in group.get_memberships():
			member=studentsById[membership.user_id]
			print(member.name)

######################################
# make a backup of the file if there is no backup within n days
def backup(ndays=0):
	sourcePath=status['dataDir'] +"PickleJar/"
	backupDir=status['dataDir'][:-1]+"-backups/"
	os.system("mkdir -p '" + backupDir + "'")
	dateString=datetime.now().strftime('%m-%d-%y')
	sourceData = []
	for root, dirs, files in os.walk(sourcePath):
		for file in files:
			sourceData.append({'fullpath': os.path.join(root,file), 'filename': file, 'inpsectionTime': int(time.time())})
	existingBackupData = []
	for root, dirs, files in os.walk(backupDir):
		for file in files:
			cretionTime = os.path.getctime(os.path.join(root,file)) # elapsed since EPOCH in float
			existingBackupData.append({'fullpath': os.path.join(root,file), 'filename': file, 'originalfilename': " ".join(file.split(" ")[:-1]), 'creationTime':cretionTime })
	newestBackup=time.time()-7*24*60*60
	for source in sourceData:
		newestBackup=int(time.time())+1
		for target in existingBackupData:
			if source['filename'] in target['filename'] and (source['inpsectionTime']  - target['creationTime'] ) < newestBackup:
				newestBackup=(source['inpsectionTime']  - target['creationTime'])
	daysSinceLastBackup=newestBackup/(60*60*24)
	#print("newest backup is " + str(int(100*daysSinceLastBackup)/100) + " days old")
	if daysSinceLastBackup > ndays:
		print("Creating backup of data...")
		for source in sourceData:
			cmd="cp -r '" + source['fullpath'] + "' '" + backupDir + source['filename'] + " " + dateString+""+"'"
			# go file-by-file copying with an added suffix for the date of backup
			#cmd="cp -r '" + sourcePath + "*' '" + backupDir + "'"
			os.system(cmd)

######################################
# Saves any data that has beem marked for saving
def saveData(listToSave=[]):
	listToSave=makeList(listToSave)
	os.system("mkdir -p '" + status['dataDir'] + "PickleJar" + "'")
	backup(4) #backup the data if there is no backup in the last 4 days
	if dataToSave['students'] or 'students' in listToSave:
		with open(status['dataDir'] + "PickleJar/" + status['prefix'] +'students.pkl', 'wb') as handle:
			pickle.dump(students, handle, protocol=pickle.HIGHEST_PROTOCOL)
		print("student data saved")
	if dataToSave['assignments'] or 'assignments' in listToSave:
		with open(status['dataDir'] +"PickleJar/" + status['prefix'] + 'assignments.pkl', 'wb') as handle:
			pickle.dump(graded_assignments, handle, protocol=pickle.HIGHEST_PROTOCOL)
		print("assignment data saved")
	if dataToSave['parameters'] or 'parameters' in listToSave:
		with open(status['dataDir'] +"PickleJar/" + status['prefix'] + 'parameters.pkl', 'wb') as handle:
			pickle.dump(params, handle, protocol=pickle.HIGHEST_PROTOCOL)	
		print("parameter data saved")
	if dataToSave['reviews']  or 'reviews' in listToSave:
		with open(status['dataDir'] + "PickleJar/" + status['prefix'] +'reviews.pkl', 'wb') as handle:
			pickle.dump([reviewsById,reviewsByCreationId, professorsReviews], handle, protocol=pickle.HIGHEST_PROTOCOL)
		print("review data saved")

######################################
# anything that needs to be done before exiting
def finish(saveBeforeExit=None):
	if saveBeforeExit==None:
		saveBeforeExit=confirm("Shall any changes be saved? ")
	if saveBeforeExit:
		saveData()
	#os._exit(1) # exits without traceback but doesn't stay in shell 
	print("Done!")

######################################
# Take an array and return a shuffled version of it 
def randomize(theArray):
	newArray=[]
	for theElement in theArray:
		newArray.append(theElement)
	random.shuffle(newArray)
	return newArray
	
######################################
# Take an object or list of objects, and return a list of objects
def makeList(obj):
	if not type(obj) == list:
		return	[obj]
	return obj
	
######################################
# Make any single char between parenthesis bold
def formatWithBoldOptions(prompt):
	stringsToReplace=[]
	for i in range(len(prompt)-2):
		if prompt[i]=="(" and prompt[i+2]==")":
			stringsToReplace.append(prompt[i:i+3])
	result=prompt
	for searchString in stringsToReplace:
		result=result.replace(searchString,"(" + "\033[1m" + searchString[1] + "\033[0m" +")")
	return result	
	
######################################
# format text to print reversed on a terminal
def reverseText(msg):
	return  "\033[7m" + msg + "\033[0m"		
	
######################################
# Prompt for user input, but give up after a timeout
	
def inputWithTimeout(prompt, timeout=10, default=None):
	import signal, threading
	prompt=formatWithBoldOptions(prompt)
	stopFlag=False
	class Countdown:
		def __init__(self):
			self._running=True
			self.inp=""
		
		def terminate(self):
			self._running = False			
	
		def run(self,n, prompt):
			msg=" "*len(str(n)) + " " + prompt 
			if default!=None:
				msg+=" [" +str(default) +"]"
			msg+= ": "
			startTime=time.time()
			elapsedTime=0
			while (elapsedTime-n < 0) and self._running:
				elapsedTime=time.time()-startTime
				timeLeftString=str(int(1+n-elapsedTime))
				msg1=Fore.GREEN  + timeLeftString + Style.RESET_ALL +msg[len(timeLeftString):] 
				if int(timeLeftString) <= 3:
					msg1=Fore.RED  + timeLeftString + Style.RESET_ALL +msg[len(timeLeftString):] 
				elif int(timeLeftString) <= 10:
					msg1=Fore.YELLOW  + timeLeftString + Style.RESET_ALL +msg[len(timeLeftString):] 
				print("\r"+msg1 + self.inp, end="")
				time.sleep(0.01)
				printLine("",False)
			print("\r",end="")
			
	def alarm_handler(signum, frame):
		raise TimeoutExpired
	
	msg=" "*len(str(timeout)) + " " + prompt + ": " #+ inparr
	cnt=Countdown()
	new_thread = threading.Thread(target=cnt.run, args=(timeout,prompt))
	new_thread.start()	
	signal.signal(signal.SIGALRM, alarm_handler)
	signal.alarm(timeout) # produce SIGALRM in `timeout` seconds
	try:
		cnt.inp=""
		key=""
		while key!="\n":
			if key!="\x7f":  #append last character as long as it isn't the backspace keu
				cnt.inp+=key
			else: #if backspace key is hit, delete last character
				cnt.inp=cnt.inp[:-1]
			key=readchar.readkey()
		val=cnt.inp
		if default!=None and val=="":
			val=default
		cnt.terminate()
		printLine("",False)
		print("\r", end="")
		time.sleep(0.02)
		signal.alarm(0)
		return str(val)
	except Exception:
		printLine("",False)
		print("\r", end="")
	signal.alarm(0)
	cnt.terminate()
	time.sleep(0.02)
	return str(default)
		
	
######################################
# print a line by printing white space
def printLine(msg="", newLine=True, line=False):
	try:
		size=os.get_terminal_size()
		cols=size.columns
	except:
		cols=80
	hideCursor()
	if (line):
		print("-"*cols)
	if newLine:
		print("\r{: <{width}}".format(msg, width=cols))		
	else:
		print("\r{: <{width}}".format(msg, width=cols),end="")
	showCursor()	

######################################
# print a line with a left and right justified text
def printLeftRight(left,right, end="\n"):
	size=os.get_terminal_size()
	cols=size.columns
	rowsOfText=1+int((len(left+right))/cols)
	hideCursor()
	print("\r",end="")
	print(f'{left:<{rowsOfText*cols-len(right)}}{right}',end=end)
	showCursor()

######################################
# print a long line with auto word wrapping
def printWithWrapping(msg):
	import textwrap, os
	size=os.get_terminal_size()
	cols=size.columns
	for line in msg.splitlines():
		print('\n'.join(textwrap.wrap(line, width=cols, replace_whitespace=False)))

######################################
# hide the cursor
def hideCursor():
	print('\033[?25l', end="")

######################################
# show the cursor
def showCursor():
	print('\033[?25h', end="")

######################################
# clear a list without redefining it.  Allows it to be kept in global scope
def clearList(lst):
	if	type(lst) == list:
		while lst:
			lst.pop()
	elif type(lst) ==dict:
		while lst:
			lst.popitem()

######################################
# exit to a debugger with instructions
def interact():
	print("Precede any commands with a '!'")
	print("Type 'c' in debugger to continue with script")
	breakpoint()
	return

######################################
# prevent the print function from displaying anything see https://stackoverflow.com/questions/8391411/how-to-block-calls-to-print
def allowPrinting(allow):
	if allow:
		 sys.stdout = sys.__stdout__
	else:
	    sys.stdout = open(os.devnull, 'w')
	    
