######################################
# Import various class definitions and other modules
errormsg=""
from datetime import datetime, timedelta
try:
	from canvasapi import Canvas
except:
	errormsg+="Missing canvasapi module.  Run 'pip install canvasapi' to intall\n"
from CanvasPeerReviews.creation import Creation
from CanvasPeerReviews.student import Student
from CanvasPeerReviews.assignment import GradedAssignment
from CanvasPeerReviews.parameters import Parameters
from CanvasPeerReviews.review import Review

import numpy as np
try:
	from dill.source import getsource	
except:
	errormsg+="Missing dill module.  Run 'pip install dill' to intall\n"
try:
	import pickle
except:
	errormsg+="Missing pickle module.  Run 'pip install pickle5' to intall\n"
import webbrowser
import copy
import random
import os
import subprocess
import csv
import math
import time
if errormsg!="":
	raise Exception(errormsg)


######################################
# Define some global variables to be used in this module
studentsById=dict()
creationsByAuthorId=dict()
reviewsById=dict()
params=Parameters()
students=[]
creations=[]
solutionURLs=dict()
graded_assignments=dict()
lastAssignment=None
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
	'dataDir': './'}


######################################
# Try loading any cached data
def loadCache():
	global course, status, params, dataDir, students, graded_assignments
	status['prefix']="course_" + str(course.id) + "_"
	status['message']=""
	try:
		with open( status['dataDir'] +status['prefix']+'students.pkl', 'rb') as handle:
			students=pickle.load(handle)
		status['students']="loaded"
		status['message']+="Loaded student data\n"
	except:
		status['students']="not loaded"
		status['message']+="Unable to find 'students.pkl'.\nThis file contains student peer review calibation data from \nany past calibrations. If you have done previous calibrations,\nyou should launch python from the directory containing the file\n"
	try:
		with open( status['dataDir'] +status['prefix']+'assignments.pkl', 'rb') as handle:
			graded_assignments=pickle.load(handle)
		status['message']+="Loaded assginment data\n"
	except:
		status['message']+="Unable to find 'assignments.pkl'.\nThis file contains grading status of any previously graded assignments.\n  You should launch python from the directory containing the file\n"
	try:
		with open(status['dataDir'] +status['prefix']+'parameters.pkl', 'rb') as handle:
			params = pickle.load(handle)
		params.loadedFromFile=True
	except:
		params=Parameters()
		params.loadedFromFile=False 
	

######################################
# delete the files that cache student data and parameters
def reset():
	global status
	try:
		os.remove(status['dataDir'] +status['prefix']+'students.pkl')
	except:
		pass
	try:
		os.remove(status['dataDir'] +status['prefix']+'parameters.pkl')
	except:
		pass
	try:
		os.remove(status['dataDir'] +status['prefix']+'solution urls.csv')
	except:
		pass

######################################
# get the course data and return students enrolled, a list of assignments 
# with peer reviews and submissions and the most recent assignment
def initialize(CANVAS_URL=None, TOKEN=None, COURSE_ID=None, dataDirectory="./Data/"):
	global course, canvas, students, graded_assignments, status
	status['dataDir']=dataDirectory
	if not os.path.exists(dataDirectory):
		os.makedirs(dataDirectory)
	printCommand=False
	if (CANVAS_URL==None or COURSE_ID==None):
		response=input("Enter the full URL for the homepage of your course: ")
		parts=response.split('/courses/')
		CANVAS_URL=parts[0]
		COURSE_ID=int(parts[1].split('/')[0])
		printCommand=True
	if (TOKEN==None):
		print("Go to canvas->Account->Settings and from the 'Approved Integrations' section, select '+New Acess Token'")
		print("More info at https://community.canvaslms.com/t5/Admin-Guide/How-do-I-manage-API-access-tokens-as-an-admin/ta-p/89")
		print("")
		TOKEN=input("Enter the token here: ")
		printCommand=True
	canvas = Canvas(CANVAS_URL, TOKEN)
	course = canvas.get_course(COURSE_ID)
	if printCommand:
		print("\nIn the future you can use \n\tinitialize('" +CANVAS_URL+ "', '"+TOKEN+"', " + str(COURSE_ID) +")"+"\nto avoid having to reenter this information\n")
	loadCache()
	#print(status['message'],end="")
	printLine(status['message'],False)
	printLine("Getting students",False)
	getStudents(course)
	printLine("Getting assignments",False)
	getGradedAssignments(course)

	lastAssignment =getMostRecentAssignment()
	for student in students:
		sections[student.section]=student.sectionName

	status["initialized"]=True
	return students, graded_assignments, lastAssignment

######################################
# Record what section a student is in
# 
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
def getStudentWork(thisAssignment='last'):
	global creations, graded_assignments, status
	if not status['initialized']:
		print("Error: You must first run 'initialize()' before calling 'getStudentWork'")
		return
	if thisAssignment=='last':
		if graded_assignments['last'] ==[]:
			for key in 	graded_assignments:
				try:
					print(key, graded_assignments[key].name)
				except:
					pass
			val=int(input("Choose the assignment id to grade: "))
			graded_assignments['last']=graded_assignments[val]
		thisAssignment=graded_assignments['last']
	submissions=thisAssignment.get_submissions()
	clearList(creations)
	i=0
	for submission in submissions:
		i+=1
		try:
			submission.courseid=thisAssignment.courseid
			submission.reviewCount=0
			submission.author=studentsById[submission.user_id]
			submission.author_id=submission.user_id
			if not submission.missing:
				creations.append(Creation(submission))
				studentsById[submission.user_id].creations[thisAssignment.id]=creations[-1]
				creationsByAuthorId[submission.user_id]=creations[-1]
				printLine("Getting submission of " + studentsById[submission.user_id].name ,False)
		except:
			status['err']="key error"
	getReviews(creations)
	status["gotStudentsWork"]=True


######################################
# Go through all of the assignments for the course and return an array of objects
# from only those assignments that are set up to require peer reviews and
# already have student submissions. 
def getGradedAssignments(course):
	assignments = course.get_assignments()
	global graded_assignments
	for i,assignment in enumerate(assignments):
		#if (assignment.peer_reviews and assignment.has_submitted_submissions): #xxx is it ok to remove the requirement that there are submissions already?
		if (assignment.peer_reviews):
			assignment.courseid=course.id
			if not assignment.id in graded_assignments: # no need to recreate if it was already loaded from the cache
				graded_assignments[assignment.id]=GradedAssignment(assignment)
			try:
				assignmentByNumber[int(''.join(list(filter(str.isdigit,graded_assignments[assignment.id].name))))]=graded_assignments[assignment.id]
			except:
				pass
	status["gotGradedAssignments"]=True


######################################
# Return the most recently due assignment of all the assignments that have peer reviews
def getMostRecentAssignment():
	global lastAssignment
	lastAssignment=None
	if len(graded_assignments)==0:
		getGradedAssignments(course)
	minTimeDelta=3650*24*3600
	offsetHours=12 # move the due dates earlier by this amount so that an assignment that is almost due will show up as the last assignment.
	
	for key, graded_assignment in graded_assignments.items():
		try:
			thisDelta=datetime.utcnow()-graded_assignment.due_at_date.replace(tzinfo=None)
			delta=thisDelta.total_seconds()
			delta+=offsetHours*3600
			if (delta > 0  and delta < minTimeDelta) :
				minTimeDelta=delta
				lastAssignment=graded_assignment
		except:
			print("Trouble getting date of",graded_assignment,", likely it was an unscedhueld assignment")
	graded_assignments['last']=lastAssignment
	if lastAssignment==None:
		print("Couldn't find an assignment with peer reviews that is past due.")
	status["gotMostRecentAssignment"]=True
	return lastAssignment

######################################
# Choose an assignment to work on
def chooseAssignment():
	global graded_assignments, lastAssignment, activeAssignment
	confirmed=False
	defaultChoice=0
	while not confirmed:
		if len(graded_assignments)-1 == len(assignmentByNumber):
			print("\nAssignments with peer reviews enabled: ")
			for key in assignmentByNumber:
				if assignmentByNumber[key] == graded_assignments['last']:
					print("\t" + str(key) +") " + assignmentByNumber[key].name + "  <---- last assignment")
					defaultChoice=key
				else:
					print("\t" + str(key) +") " + assignmentByNumber[key].name )
			val=getNum("Enter a number for the assignment to work on", defaultVal=defaultChoice)
			if val in assignmentByNumber:
				confirmed=confirm("You have chosen " + assignmentByNumber[val].name)
			else:
				confirmed=False
				print("Invalid choice")
			if confirmed:
				activeAssignment=assignmentByNumber[val]
		else:
			i=1
			assignmentKeyByNumber=dict()
			print("\nAssignments with peer reviews enabled: ")
			for key in graded_assignments:
				if (key != 'last'):
					if graded_assignments[key] == graded_assignments['last']:
						print("\t" + str(i) +") " + graded_assignments[key].name + "  <---- last assignment")
						defaultChoice=i
					else:
						print("\t" + str(i) +") " + graded_assignments[key].name)
					assignmentKeyByNumber[i]=key
					i+=1
			val=getNum("Enter a number for the assignment to work on", defaultVal=defaultChoice, limits=[1,i])
			confirmed=confirm("You have chosen " + graded_assignments[assignmentKeyByNumber[val]].name)
			if confirmed:
				activeAssignment=graded_assignments[assignmentKeyByNumber[val]]
	#print("using key " + str(assignmentKeyByNumber[val]))
	return activeAssignment


######################################
#This takes a list of submissions which are to be used as calibration reviews
# and assigns one to each student in the class, making sure to avoid assigning
# a calibration to its own author if possible
def assignCalibrationReviews(calibrations="auto"):
	global status, creations
	if not status['initialized']:
		print("Error: You must first run 'initialize()' before calling 'assignCalibrationReviews'")
		return
	elif not status['gotStudentsWork']:
		print("getting student work")
		getStudentWork()
	if calibrations=="auto":
		professorReviewedSubmissionIDs=[r.submission_id for r in professorsReviews[graded_assignments['last'].id]]
		calibrations=[c for c in creations if (c.id in professorReviewedSubmissionIDs)]
		#return
	else:
		creations=calibrations

	studentsWithSubmissions=[studentsById[c.author_id] for c in creations if studentsById[c.author_id].role=='student']
	reviewers=randmoize(studentsWithSubmissions) 
	
	print("studentsWithSubmissions ->" , len(studentsWithSubmissions))

	calibrations=makeList(calibrations)
	print("Professor has already graded submissions by ", end="")
	for c in calibrations:
		if c!=calibrations[-1]:
			print(c.author.name,end=",")
		else:
			print(" and " + c.author.name)			
	i=0
	for reviewer in reviewers:
		tic=time.time()
		while (	time.time()-tic < 1 and ((reviewer.id == calibrations[i%len(calibrations)].author_id) or  (studentsById[reviewer.id].section != studentsById[calibrations[i%len(calibrations)].author_id].section ))):
			i+=1
		if not time.time()-tic  <1:
			raise Exception("Timeout error assigning calibration reviews - perhaps the professor hasn't yet graded an assignment frmo each section?")
			return
		calibration = calibrations[i%len(calibrations)]
		printLine(str(i)+"assigning" +str(studentsById[calibrations[i%len(calibrations)].author_id].name) +"'s work (" + studentsById[calibrations[i%len(calibrations)].author_id].sectionName +") to be reviewed by "+ studentsById[reviewer.id].name+ "(" ,studentsById[reviewer.id].sectionName + ")", False )
		i+=1
		if (studentsById[calibrations[i%len(calibrations)].author_id].name!=studentsById[reviewer.id].name):
			calibration.create_submission_peer_review(reviewer.id)
		else:
			printLine("skipping self review", False)
		if not calibration.assignment_id in reviewer.reviewCount:
			reviewer.reviewCount[calibration.assignment_id]=0
		reviewer.reviewCount[calibration.assignment_id]+=1
		calibration.reviewCount+=1
	######### Save student data for future sessions #########	
	with open(status['dataDir'] +status['prefix'] + 'students.pkl', 'wb') as handle:
		pickle.dump(students, handle, protocol=pickle.HIGHEST_PROTOCOL)

	
######################################
# Takes a student submission and a list of potential reviewers, and the number of reviews 
# to assign and then interacts with canvas to assign that number of reviewers to peer
# review the submission.  It will select reviewers from the beginning of the list of
# potential reviewers skipping over anyone who has already been assigned at least the
# target number of reviews.
#xxx need to ensure reviews are assigned to students in the same section
def assignPeerReviews(creationsToConsider, reviewers="randomize", numberOfReviewers=999999):
	startTime=time.time()

	global status
	if not status['initialized']:
		print("Error: You must first run 'initialize()' before calling 'assignPeerReviews'")
		return
	elif not status['gotStudentsWork']:
		getStudentWork()
		
	countAssignedReviews(creationsToConsider)
	creationList=makeList(creationsToConsider)
	#countAssignedReviews(creationList) #is this necessary?
	studentsWithSubmissions=[studentsById[c.author_id] for c in creations if studentsById[c.author_id].role=='student']
	peersWithSubmissions=[x for x in studentsWithSubmissions if x.role=='student']
	graders=[x for x in students if x.role=='grader']
	graders=randmoize(graders)
	if reviewers=="randomize":
		peersWithSubmissions=randmoize(peersWithSubmissions) 
	reviewers=makeList(peersWithSubmissions)
	#assign params.numberOfReviews reviews per creation
	for creation in creationList:
		for reviewer in reviewers:
			if not creation.assignment_id in reviewer.reviewCount:
				reviewer.reviewCount[creation.assignment_id]=0
			if (reviewer.reviewCount[creation.assignment_id] < params.numberOfReviews and creation.reviewCount < numberOfReviewers and reviewer.id != creation.user_id and reviewer.section == studentsById[creation.user_id].section):
					creation.create_submission_peer_review(reviewer.id)
					reviewer.reviewCount[creation.assignment_id]+=1
					creation.reviewCount+=1
					print("assigning " + str(reviewer.name)	 + " to review " + str(creation.author.name) + "'s creation")			
	# now that all creations have been assigned the target number of reviews, keep assigning until all students have the target number of reviews assigned
	for reviewer in reviewers:
		tic=time.time()
		while (reviewer.reviewCount[creationList[0].assignment_id] < params.numberOfReviews and time.time()-tic < 1):
			creation=random.choice(creationList)
			if (reviewer.section == studentsById[creation.user_id].section):
				creation.create_submission_peer_review(reviewer.id)
				reviewer.reviewCount[creation.assignment_id]+=1
				creation.reviewCount+=1
				print("assigning " + str(reviewer.name)	 + " to review " + str(creation.author.name) + "'s creation")			
	if len(graders)==0:
		return
	# finally assign to graders
	sections=dict()
	for grader in graders:
		sections[grader.section] = grader.sectionName
	for key in sections:
		thisSectionsGraders=[x for x in students if (x.role=='grader' and x.section == key)]
		thisSectionsCreations=[x for x in creationList if (x.author.section == key)]
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
			for creation in creationsListofList[i]:
				if not creation.assignment_id in reviewer.reviewCount:
					reviewer.reviewCount[creation.assignment_id]=0
				if (reviewer.id != creation.user_id ):
					creation.create_submission_peer_review(reviewer.id)
					reviewer.reviewCount[creation.assignment_id]+=1
					creation.graderReviewCount+=1
					print("assigning grader " + str(reviewer.name)	 + " to review " + str(creation.author.name) + "'s creation")			
	######### Save student data for future sessions #########	
	with open(status['dataDir'] +status['prefix'] + 'students.pkl', 'wb') as handle:
		pickle.dump(students, handle, protocol=pickle.HIGHEST_PROTOCOL)
	
			
######################################
# Get a list of all students enrolled in the course.  Return an array of Student objects
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
		except:
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
	placeholder="solution URLs go here"
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
		if success:
			return solutionURLs[assignment.id]
	except:
		f = open(fileName, "w")
		f.write("Assignment Name, Solution URL\n")
		for key, assignment in graded_assignments.items():
			f.write(assignment.name + ", " + placeholder +"\n")
		f.close()
		subprocess.call(('open', fileName))
		print("Put the solution URLs into the file '" + fileName + "'")
	return ""

# ######################################
# Count how many reviews have been assigned to each student using data from Canvas
def countAssignedReviews(creations):
	#when append=True it will check how many review have already been assigned which is slow (takes about a minute).  When append=False it will set the review count to zero.
	global students
	creations=makeList(creations)
	#for student in students:
	#	clearList(student.reviewCount)
	print("commented out lines 487-488 in utilites that clears the student reviewcount")
	for student in students:
		student.reviewCount[creations[0].assignment_id]=0	
	print("Checking how many peer reviews each students has already been assigned...")
	for i,creation in enumerate(creations):
		printLine("    " +str(i) + "/" + str(len(creations)) +" Checking reviews of " + creation.author.name, False)
		for thesePeerReviews in creation.get_submission_peer_reviews():
			if thesePeerReviews.assessor_id in studentsById:
				reviewer=studentsById[thesePeerReviews.assessor_id]
				if not creation.assignment_id in reviewer.reviewCount:
					reviewer.reviewCount[creation.assignment_id]=0				
				reviewer.reviewCount[creation.assignment_id]+=1	
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
		msg+="\t" + criteriaDescription[d['criterion_id']] 
		try:
			msg+=" [" + str(d['points']) + "]"
		except:
			msg+=" [missing]"
		try:
			msg+=" "+d['comments']
		except:
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
def getReviews(creations):
	global course
	rubrics=course.get_rubrics()
	allReviews=[]
	for rubric in rubrics:
		rubric=course.get_rubric(rubric.id,include='assessments', style='full')
		if hasattr(rubric, 'assessments'):
			for creation in creations:
				for assessment in rubric.assessments:
					if ((assessment['assessment_type']=='grading' or assessment['assessment_type']=='peer_review') and creation.id == assessment['artifact_id'] ):
						data=assessment['data']
						reviewer_id = assessment['assessor_id']
						review_type = assessment['assessment_type']
						review=Review(review_type, reviewer_id, creation.user_id, creation.assignment_id, creation.id, data)
						alreadyProcessed = any(thisReview.fingerprint() == review.fingerprint() for thisReview in studentsById[creation.user_id].reviewsReceived)
						if not alreadyProcessed:
							studentsById[creation.user_id].reviewsReceived.append(review)
						else: 
							pass
						if creation.assignment_id in studentsById[creation.user_id].regrade: # replace entry
							for i,thisReview in enumerate(studentsById[creation.user_id].reviewsReceived):
								if thisReview.fingerprint() == review.fingerprint() and assessment['assessment_type']=="grading":
									studentsById[creation.user_id].reviewsReceived[i]=review			
						if creation.id in reviewsById:
							reviewsById[creation.id].append(review)
						else:
							reviewsById[creation.id]=[review]
						if assessment['assessment_type']=='grading':
							if creation.assignment_id in professorsReviews:
								professorsReviews[creation.assignment_id].append(review)
							else:
								professorsReviews[creation.assignment_id]=[review]
						elif reviewer_id in studentsById:
							# if not already assigned assignment.multiplier[cid]
							studentsById[reviewer_id].reviewsGiven[review.submission_id]=review
						allReviews.append(review)
	status["gotReviews"]=True
	return allReviews
	
######################################
# Compare the peer reviews students gave to the peer reviews of the same submission 
# given by others.	An average deviation is computed using a weighting factor based on 
# the performance of the other students on their previous reviews.	If the submission
# being reviewed was also graded by the instructor, the deviation from the instructor's
# review will more heavily weighted.  The results are save as a "grading power" for the 
# student in the Student object.  This grading power is used for future calibrations,
# and is used as a weighting factor when assigning grades to students they reviewed.
def calibrate(studentsToCalibrate="all"):
	if (studentsToCalibrate=="all"):
		studentsToCalibrate=students
	global status
	if not status['initialized']:
		print("Error: You must first run 'initialize()' before calling 'calibrate'")
		return
	cids=dict()
	for student in studentsToCalibrate:
		uncalibratedReviews=False
		for key,thisGivenReview in student.reviewsGiven.items():
			uncalibratedReviews=uncalibratedReviews or (not thisGivenReview.submission_id in student.submissionsCalibratedAgainst)
		if uncalibratedReviews:
			# reduce the weight of previous calibrations
			for cid in student.delta2:
				student.delta2[cid]*=params.weeklyDegradationFactor()
				student.delta[cid]*=params.weeklyDegradationFactor()
				student.numberOfComparisons[cid]*=params.weeklyDegradationFactor()
		for key,thisGivenReview in student.reviewsGiven.items():
			#student.assignmentsCalibrated[thisGivenReview.assignment_id]=datetime.now()
			blankCreation=len([c for c in creations if c.id == key and c.missing])>0
			alreadyCalibratedAgainst=thisGivenReview.submission_id in student.submissionsCalibratedAgainst
			if not blankCreation and not alreadyCalibratedAgainst: #don't bother if creation is blank or we've already calibrated against this review 
				student.submissionsCalibratedAgainst[thisGivenReview.submission_id]=True
				for otherReview in reviewsById[thisGivenReview.submission_id]:
					if (otherReview.reviewer_id != student.id): #don't compare this review to itself
						for cid in thisGivenReview.scores:
							cids[cid]=True
							temp=criteriaDescription[cid]
							student.criteriaDescription[cid]=temp
							if not cid in student.delta2:
								student.delta2[cid]=0
								student.delta[cid]=0
								student.numberOfComparisons[cid]=0 
							if otherReview.review_type == "peer_review" and otherReview.reviewer_id in studentsById:
								if (studentsById[otherReview.reviewer_id]).role == 'grader':
									weight=params.gradingPowerForGraders
								else:
									weight=studentsById[otherReview.reviewer_id].getGradingPower(cid); 
							elif otherReview.review_type == "grading":
								weight=params.gradingPowerForInstructors
							if (cid in student.delta2) and (cid in thisGivenReview.scores) and (cid in otherReview.scores):
								student.delta2[cid]+=weight*(thisGivenReview.scores[cid] - otherReview.scores[cid] )**2 
								student.delta[cid]+=weight*(thisGivenReview.scores[cid] - otherReview.scores[cid] ) 
								student.numberOfComparisons[cid]+=weight		
	#		Use the previously calculated rms-like deviation from other reviewers to calculate a grading power
	#		for this student
	for student in students:
		student.updateGradingPower()

	#		Now that all of the students grading powers have been updated, normalize everything so that the average
	#		grading power for all of the students is 1
	for cid in cids:
		total, numberCounted = 0 , 0
		for student in students:
			if cid in student.rms_deviation_by_category: 
				total+=student.getGradingPower(cid)
				numberCounted+=1
		else:
			student.gradingPower[cid]=1
		for student in students:
			if cid in student.rms_deviation_by_category:
				student.gradingPowerNormalizatoinFactor[cid]*=total/numberCounted
			else:
				student.gradingPowerNormalizatoinFactor[cid]=1

	######### Save student data for future sessions #########	
	with open(status['dataDir'] +status['prefix'] + 'students.pkl', 'wb') as handle:
		pickle.dump(students, handle, protocol=pickle.HIGHEST_PROTOCOL)
	status["calibrated"]=True

######################################
# adjust point distribution for a specific assignment
def overrideDefaultPoints(assignment):
	for cid in assignment.criteria_ids():
		val=getNum("How many points (out of 100) should be awarded for '" + criteriaDescription[cid]+ "'?", params.pointsForCid(cid, assignment.id))
		params.pointsForCid(cid,assignment.id ,val)
	#save the parameters
	with open(status['dataDir'] +status['prefix'] + 'parameters.pkl', 'wb') as handle:
		pickle.dump(params, handle, protocol=pickle.HIGHEST_PROTOCOL)	

######################################
# Process a list of students (or all of the students, calling the
# gradeStudent function for each
def grade(assignment, studentsToGrade="All", reviewGradeFunc=None):
	global status
	if not status['initialized']:
		print("Error: You must first run 'initialize()' before calling 'grade'")
		return		
	if isinstance(studentsToGrade, str) and studentsToGrade.lower()=="all":
		for student in makeList(students):
			gradeStudent(assignment, student, reviewGradeFunc)
	else:
		for student in makeList(studentsToGrade):
			gradeStudent(assignment, student, reviewGradeFunc)
	assignment.graded=True
	status["graded"]=True
	msg=assignment.name +  " graded with the following point values:\n"
	if status["regraded"]:
		msg=assignment.name +  " regraded with the following point values:\n"
	
	for cid in assignment.criteria_ids():
		msg+= "\t(" +str(params.pointsForCid(cid,assignment.id ))+ ") " + criteriaDescription[cid] + "\n"
	msg+="Using the following curve '" + assignment.curve + "'\n"
	log(msg)
	getStatistics(assignment, text=False, hist=False)
	######### Save student and assignment data for future sessions #########	
	with open(status['dataDir'] +status['prefix'] + 'assignments.pkl', 'wb') as handle:
		pickle.dump(graded_assignments, handle, protocol=pickle.HIGHEST_PROTOCOL)
	with open(status['dataDir'] +status['prefix'] + 'students.pkl', 'wb') as handle:
		pickle.dump(students, handle, protocol=pickle.HIGHEST_PROTOCOL)


######################################
# Check for any work that is unreviewed.
def checkForUnreviewed(assignment, openPage=False):	
	graderIDs=[x.id for x in students if x.role=='grader']
	mostNumberOfReviewsReceived=0
	for creation in creations:
		student=creation.author	
		mostNumberOfReviewsReceived=max(mostNumberOfReviewsReceived,student.numberOfReviewsReceivedOnAssignment(assignment.id))

	creationsByNumberOfReviews=[0]*(mostNumberOfReviewsReceived+1)
	for n in range(mostNumberOfReviewsReceived+1):
		creationsByNumberOfReviews[n]=[c for c in creations if c.author.numberOfReviewsReceivedOnAssignment(assignment.id)==n and c.author.role=='student']
				
	if len(creationsByNumberOfReviews[0])==0 and len(creationsByNumberOfReviews[1])==0:
		print("All creations have been reviewed at least twice")
	else:
		if len(creationsByNumberOfReviews[0])==0 :
			print("All creations have been reviewed at least once")
		fileName=status['dataDir'] + assignment.name + "_todo.html"
		f = open(fileName, "w")
		f.write("<html><head><title>Submissions by number of completed reviews</title><style>\n")
		f.write(".instructor {color: blue;}\n.grader {color: green;}\n.student {color: black;}\n")
		f.write("a {text-decoration:none}\n")
		f.write("a.instructor:link {color: #0000ff;}\n")
		f.write("a.instructor:hover {color: #440044;}\n")
		#f.write("a.instructor:visited {text-decoration:line-through;}\n")
		f.write("a.grader:link {color: #008000;}\n")
		f.write("a.grader:hover {color: #440044;}\n")
		#f.write("a.grader:visited {text-decoration:line-through;}\n")
		f.write("a.student:link {color: #000000;}\n")
		f.write("a.student:hover {color: #440044;}\n")
		#f.write("a.student:visited {text-decoration:line-through;}\n")
		colors = ["#ffeeee", "#eeeeff"]		
		ind=0
		for key in sections:
			ind=(ind+1)%len(colors)
			#f.write(".sec"+sections[key][-2:] + "{background-color : " + colors[ind] +";}") 
		f.write("</style></head><body>\n")
		f.write("<h3>Submissions for "+assignment.name+" by number of completed reviews:</h3>\n<ul>\n")
		f.write("<span class='instructor'>Graded by instructor</span> | ")
		f.write("<span class='grader'>Graded by grader</span> | ")
		f.write("<span class='student'>Only graded by peers</span>\n")

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
					gradedByInstructor=len([r for r in creation.author.reviewsReceived if r.review_type=='grading' and r.assignment_id ==assignment.id])>0
					gradedByGrader=len([r for r in creation.author.reviewsReceived if r.reviewer_id in graderIDs and r.assignment_id ==assignment.id])>0
					if creation.author.sectionName == section:
						url=creation.preview_url.replace("assignments/","gradebook/speed_grader?assignment_id=").replace("/submissions/","&student_id=").replace("?preview=1&version=1","")
						f.write("<a href='"+ url +"' target='_blank' class='")
						if (gradedByInstructor):
							f.write("instructor")
						elif gradedByGrader:
							f.write("grader")
						else:
							f.write("student")			
						f.write( "'> "+creation.author.name + "</a><br>\n")
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
# Go through all submissions for an assignment. If the assignment was created by
# a student in the list of students given, determine a grade for the submission
# based on a weighted average of peer reviews, or using the instructors grade if it
# was graded by the instructor.	 Then look through all the reviews the students in the
# given list of students performed on this assignment and computer a grade for their
# peer reviews based on a weighted average of the deviation from other reviewers.
# finally combine these two grades to get a total grade, and record all three grades
# into the student object, along with comments that can be shared with the student
# explaining the grade		
def gradeStudent(assignment, student, reviewGradeFunc=None):
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
		multiplier=params.pointsForCid(cid, assignment.id)
		for review in student.reviewsReceived:
			if review.assignment_id == assignment.id:
				weight=0
				creationWasReviewed=True
				role=""
				gradingExplanationLine=""
				if (review.reviewer_id in studentsById):
					role=studentsById[review.reviewer_id].role
				if review.review_type == "peer_review" and not (assignment.id in student.assignmentsGradedByInstructor):
					if role == 'grader':
						weight=params.gradingPowerForGraders
						gradingExplanationLine="Review [G"+ str(review.reviewer_id) +"_" + str(cid) +"] "
					elif role== 'student':
						weight=studentsById[review.reviewer_id].getGradingPower(cid); 
						gradingExplanationLine="Review [P"+ str(review.reviewer_id)+"_" + str(cid) +"] "
				elif review.review_type == "grading":
					gradingExplanationLine="Review [I"+ str(review.reviewer_id)+"_" + str(cid) +"] "
					weight=params.gradingPowerForInstructors
				if cid in review.scores:
					try:
						reviewer=studentsById[review.reviewer_id]
						compensation=reviewer.deviation_by_category[cid]*params.compensationFactor
						compensation=min(compensation, params.maxCompensationFraction* multiplier)
						compensation=max(compensation, -params.maxCompensationFraction* multiplier)
					except:
						compensation=0			
					gradingExplanationLine+=" Grade of {:.2f} with an adjustment for this grader of {:+.2f} and a relative grading weight of {:.2f}".format(review.scores[cid], compensation, weight)
					if not (str(review.reviewer_id)+"_" + str(cid)) in student.gradingExplanation:
						student.gradingExplanation += "    "  + gradingExplanationLine + "\n"
					total+=max(0,min((review.scores[cid] - compensation)*weight, assignment.criteria_points(cid)*weight)) # don't allow the compensation to result in a score above 100% or below 0%%
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
		else:
			if student.creations[assignment.id].submitted_at != None:
				creationGrade=100 # Change this
				student.gradingExplanation+=""#"This submission was not reviewed.  Placeholder grade of " + str(creationGrade) + " assigned\n"
				print("No reviews of",student.name,"on assignment",assignment.name, "assigning placeholder grade of", creationGrade)

	#calculate review grades
	delta2=0
	tempDelta=dict()
	tempTotalWeight=dict()
	numberOfComparisons=0
	student.reviewGradeExplanation=""
	for key, thisGivenReview in student.reviewsGiven.items():
		blankCreation=len([c for c in creations if c.id == key and c.missing])>0	
		if thisGivenReview.assignment_id == assignment.id and not blankCreation:
			for otherReview in reviewsById[thisGivenReview.submission_id]:
				if (otherReview.reviewer_id != student.id): #don't compare this review to itself
					for cid in thisGivenReview.scores:
						if otherReview.review_type == "peer_review":
							try:
								weight=studentsById[otherReview.reviewer_id].getGradingPower(cid); 
								if (studentsById[otherReview.reviewer_id]).role == 'grader':
									weight=params.gradingPowerForGraders
							except:
								weight=1
							
						elif otherReview.review_type == "grading":
							weight=params.gradingPowerForInstructors

						try:
							if cid in tempDelta:
								tempDelta[cid]+=weight*(thisGivenReview.scores[cid] - otherReview.scores[cid] )
								tempTotalWeight[cid]+=weight
							else:
								tempDelta[cid]=weight*(thisGivenReview.scores[cid] - otherReview.scores[cid] )		
								tempTotalWeight[cid]=weight						
							delta2+=weight*((thisGivenReview.scores[cid] - otherReview.scores[cid] )/ assignment.criteria_points(cid))**2
							numberOfComparisons+=weight 
						except:
							status['err']="Key error" 
	for cid in tempDelta:
		student.reviewGradeExplanation+="For '" + str(criteriaDescription[cid]) + "' you graded on average " 
		if (tempDelta[cid]>0.05):
			student.reviewGradeExplanation+=str(int(100*tempDelta[cid]/tempTotalWeight[cid])/100) + " points higher than other graders\n"
		elif (tempDelta[cid]<-0.05):
			student.reviewGradeExplanation+=str(int(-100*tempDelta[cid]/tempTotalWeight[cid])/100) + " points lower than other graders\n"
		else:
			student.reviewGradeExplanation+=" about the same as other graders\n"

	rms=2
	
	if numberOfComparisons!=0:
		rms=(delta2/numberOfComparisons)**0.5
	try:
		reviewCount=student.reviewCount[creation.assignment_id]
	except:
		reviewCount=params.numberOfReviews

	if reviewGradeFunc == None:
		reviewGrade=min(1,student.numberOfReviewsGivenOnAssignment(assignment.id)/reviewCount) * max(0,min(100, 120*(1-rms)))
	else:
		reviewGrade=reviewGradeFunc(rms)
	if (reviewGrade<100):
		student.reviewGradeExplanation+="Your review grade will improve as it aligns more closely with other graders"
	else:
		student.reviewGradeExplanation+="Keep up the good work on your reviews"
		

	totalGrade=creationGrade * params.weightingOfCreation + reviewGrade * params.weightingOfReviews
	
	#adjust the points from a scale of 100 down to the number of points for the assingmnet
	digits=int(2-math.log10(assignment.points_possible))
	creationPoints=round(creationGrade*assignment.points_possible/100.0*  params.weightingOfCreation ,digits)
	reviewPoints=round(reviewGrade*assignment.points_possible/100.0 * params.weightingOfReviews ,digits)
	if (digits ==0):
		creationPoints=int(creationPoints)
		reviewPoints=int(reviewPoints)
	totalPoints=creationPoints + reviewPoints
	curvedTotalPoints=curveFunc(totalPoints)
	if not assignment.id in student.creations:
		curvedTotalPoints=0 # no submission

	student.grades[assignment.id]={'creation': creationGrade, 'review':  reviewGrade, 'total' :totalGrade, 'curvedTotal': curvedTotalPoints}
	student.points[assignment.id]={'creation': creationPoints, 'review':  reviewPoints, 'total' :totalPoints, 'curvedTotal': curvedTotalPoints}
	percentileRanking=gradingPowerRanking(student, percentile=True)
	
	if (assignment.id in student.regrade and student.regrade[assignment.id]=="Started"):
		msg="View the rubric table above to see details of your regrade.\n"
		msg+="In total you received " + str(student.points[assignment.id]['creation']) + " points for your creation, "
		msg+=" and " + str(student.points[assignment.id]['review']) + " points for your reviews, "
		msg+=" giving a total of " + str(student.points[assignment.id]['total']) + " points"
		if (assignment.curve!='x'):
			msg+=" that when curved gives a score of " + str(student.points[assignment.id]['curvedTotal'])
		student.regradeComments[assignment.id]=msg
	if student.numberOfReviewsGivenOnAssignment(assignment.id)==0:
		student.reviewGradeExplanation="You did not completeany of your peer reviews, so your review grade was 0.  "

	student.comments[assignment.id]=student.reviewGradeExplanation
	if (percentileRanking >66):
		student.comments[assignment.id]+=(("\n\nBased on comparisons of your reviews to those of other students, the graders and the instructor, your reviewing quality is in the %dth percentile.  Good job - as one of the better graders in the class your peer reviews will carry additional weight.") % (percentileRanking ) )	
	elif (percentileRanking <33):
		student.comments[assignment.id]+=(("\n\nBased on comparisons of your reviews to those of other students, the graders and the instructor, your reviewing quality is in the %dth percentile.  You can improve your ranking (and your review scores) by carefully following the grading rubric.") % (percentileRanking ) )	
	else:
		student.comments[assignment.id]+=(("\n\nBased on comparisons of your reviews to those of other students, the graders and the instructor, your reviewing quality is in the %dth percentile.") % (percentileRanking ) )	
	if (curvedTotalPoints==totalPoints):
		student.comments[assignment.id]+=(("  You earned %." + str(digits) +"f out of  %.f points for your submission and %." + str(digits) +"f points out of %.f for your reviews giving you a score of %." + str(digits) +"f points.\n\n If you believe the peer reviews of your work have a significant error, explain in a comment in the next few days and include the word 'regrade' to have it double checked.") % 
		(creationPoints, 100*params.weightingOfCreation, reviewPoints, 100*params.weightingOfReviews, totalPoints ) )
	else:
		student.comments[assignment.id]+=(("  You earned %." + str(digits) +"f out of  %.f points for your submission and %." + str(digits) +"f points out of %.f for your reviews giving you a raw score of %." + str(digits) +"f points.  This was curved to give an adjusted score of %." + str(digits) +"f.\n\n  If you believe the peer reviews of your work have a significant error, explain in a comment in the next few days and include the word 'regrade' to have it double checked.") % 
		(creationPoints, 100*params.weightingOfCreation, reviewPoints, 100*params.weightingOfReviews, totalPoints, curvedTotalPoints ) )
	
	if not assignment.id in student.creations:
		student.gradingExplanation+="No submission received"
		student.comments[assignment.id]="No submission received"

######################################
# find submissions that need to be regraded as based on the word regrade in the comments

def regrade(assignmentList=None, studentsToGrade="All", reviewGradeFunc=None, recalibrate=True):
	global status, activeAssignment
	if not status['initialized']:
		print("Error: You must first run 'initialize()' before calling 'regrade'")
		return
	if assignmentList==None:
		assignmentList=[g for g in graded_assignments.values() if g.graded]
	assignmentList=makeList(assignmentList)
	for assignment in assignmentList:
		print("\nRegrading " + assignment.name + "...")
					
		regradedStudents=dict()
		keyword="regrade" # if this keyword is in the comments flag the submission for a regrade
		#make list of students needing a regrade
		if studentsToGrade.lower()=="all":
			for i,student in enumerate(makeList(students)):
				for key in student.creations:
					c = student.creations[key]
					printLine("Checking for a regrade request from " + student.name + " " + str(i+1)+"/"+str(len(makeList(students))),newLine=False) 
					try:
						if c.assignment_id == assignment.id and str(c.edit().submission_comments).lower().count(keyword)>1:
							if not (assignment.id in student.regrade): 
								regradedStudents[c.edit().id]=student
								printLine(student.name + " has a regrade request pending")
					except:
						pass
			printLine("",newLine=False)
		else:
			for student in makeList(studentsToGrade):
				for key in student.creations:
					c = student.creations[key]
					if c.assignment_id == assignment.id and str(c.edit().submission_comments).lower().count(keyword)>1:
						if not (assignment.id in student.regrade):
							regradedStudents[c.edit().id]=student
		#process list of students needing a regrade
		for student_key in regradedStudents:
			student=regradedStudents[student_key]
			for key in student.creations:
				c = student.creations[key]
				if c.assignment_id == assignment.id and str(c.edit().submission_comments).lower().count(keyword)>0:
					comments=[com['comment'] for com in c.edit().submission_comments if keyword in com['comment'].lower()]
					#print("regrade requested by " + student.name + "for assignment at: ")
					previewUrl=c.edit().preview_url.replace("preview=1&","")
					#webbrowser.open(previewUrl)
					#print(previewUrl)
					print("\n---------- " + student.name + " says: ---------- \n")
					print("\n\n".join(comments[1:])+"\n")
					#print("With comments: " + "\n\n".join(comments[1:]) + "\n")
					val="unknwon"
					while not val in ["i","f","v",""]:
						val=input("\t(v) to view student work \n\t(i) to ignore this request for now\n\t(f) to forget it forever\n\t<enter> to accept\n")
						if val=='i' and assignment.id in student.regrade:
							student.regrade.pop(assignment.id)
						if val=='f':
							student.regrade[assignment.id]="ignore"
						if val=="v":
							val="unknwon"
							print("Enter any regrade info and comments into the web browser")
							webbrowser.open(previewUrl)
						if val=="":
							student.regrade[assignment.id]="Started"
		print("\n")
		status["regraded"]=True
		assignment.regraded=True
		msg=assignment.name +  " regraded with the following point values:\n"
		for cid in assignment.criteria_ids():
			msg+= "\t(" +str(params.pointsForCid(cid,assignment.id ))+ ") " + criteriaDescription[cid] + "\n"
		log(msg,False)

	getStudentWork(assignment)
	if (recalibrate):
		calibrate()
	grade(assignment, studentsToGrade=list(regradedStudents.values()), reviewGradeFunc=reviewGradeFunc)
	for student_key in regradedStudents:
		student=regradedStudents[student_key]
		if assignment.id in student.regrade and student.regrade[assignment.id]!="ignore" and student.regrade[assignment.id]!="Done":
			printLine("Posting regrade comments for " + student.name, newLine=False)
			student.comments[assignment.id]=student.regradeComments[assignment.id]
			postGrades(assignment, listOfStudents=[student])
			student.regrade[assignment.id]="Done"
	printLine()
	#postGrades(assignment, listOfStudents=list(regradedStudents.values()))
	######### Save student data for future sessions #########	
	with open(status['dataDir'] +status['prefix'] + 'students.pkl', 'wb') as handle:
		pickle.dump(students, handle, protocol=pickle.HIGHEST_PROTOCOL)
	


######################################
# For the assignment given, post the total grade on canvas and post the associated
# comments.	 The optional arguments allow you to suppress posting comments or the grades
def postGrades(assignment, postGrades=True, postComments=True, listOfStudents='all'):
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
				creation.edit(comment={'text_comment':student.comments[assignment.id]})
		else:
			printLine("No creation to post for " + student.name, newLine=False)
	printLine()
	assignment.gradesPosted=True	
	######### Save assignment data for future sessions #########	
	with open(status['dataDir'] +status['prefix'] + 'assignments.pkl', 'wb') as handle:
		pickle.dump(graded_assignments, handle, protocol=pickle.HIGHEST_PROTOCOL)
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
	#getStudentWork(thisAssignment)
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

				except:
					status['err']="unable to process test student"
	thisAssignment.gradesPosted=True	
	######### Save assignment data for future sessions #########	
	with open(status['dataDir'] +status['prefix'] + 'assignments.pkl', 'wb') as handle:
		pickle.dump(graded_assignments, handle, protocol=pickle.HIGHEST_PROTOCOL)
	log("Grades for " +thisAssignment.name+ " posted via file'" + fileName + "'")
	status["posted"]=True

######################################
# If the grading parameters were not available in a saved file, prompt the user
# for these.  These parameters are used to define things like the weighting of
# various rubric criteria, and the weighting of the submission score versus the 
# review score.	 The results get saved to a file so they don't need to be 
# reentered everytime the script is run
def getParameters(ignoreFile=False):
	global status, criteriaDescription, params
	if ignoreFile:
		params=Parameters()
		params.loadedFromFile=False
	logFile = open(status['dataDir'] +status['prefix'] + 'parameters.log', "a") 	
	headerWritten=False

	for key, assignment in graded_assignments.items():
		if assignment != []:
			needInput=False
			for criteria in assignment.rubric:
				criteriaDescription[criteria['id']]=criteria['description']
				if not criteria['id'] in params.multiplier:
					needInput=True
			if needInput:
				if not headerWritten:
					logFile.write("----" + str(datetime.now()) + "----\n")
					headerWritten=True
				print("Need to assign criteria weightings for the rubric assigned to " + assignment.name + ": ")
				for criteria in assignment.rubric:
					if not criteria['id'] in params.multiplier: 
						print("\t" + criteria['description'])
					else:
						print("\t" + criteria['description'] + " (" + str(params.multiplier[criteria['id']]) +")")
					
				for criteria in assignment.rubric:
					criteriaDescription[criteria['id']]=criteria['description']
					if not criteria['id'] in params.multiplier:
						params.multiplier[criteria['id']]=getNum("How many points (out of 100) should\n\t" +criteria['description'] + "\nbe worth? ",limits=[0,100], fileDescriptor=logFile)
						#val=float(input("\nHow many points (out of 100) should\n\t" +criteria['description'] + "\nbe worth? "))
						#params.multiplier[criteria['id']]=val
						#logFile.write(How many points (out of 100) should\n\t" +criteria['description'] + "\nbe worth?: " + str(val))
	if not params.loadedFromFile or ignoreFile:
		weightingOfCreation=getNum("Enter the relative weight of the creation towards the total grade",0.7, fileDescriptor=logFile)
		weightingOfReviews=getNum("Enter the relative weight of the review towards the total grade",0.3, fileDescriptor=logFile)
		total=weightingOfCreation+weightingOfReviews
		params.weightingOfCreation=weightingOfCreation/total
		params.weightingOfReviews=weightingOfReviews/total
		params.numberOfReviews=getNum("How many reviews should be assigned to each student?",3, fileDescriptor=logFile)	
		params.peerReviewDurationInDays=getNum("How many days should the students have to complete their peer reviews?",3, fileDescriptor=logFile)
		params.gradingPowerForInstructors=getNum("How many times greater than a student should an instructors grading be weighted?",10, fileDescriptor=logFile)
		params.gradingPowerForGraders=getNum("How many times greater than a student should  student graders grading be weighted?",5, fileDescriptor=logFile)
		params.halfLife=getNum("How many assignments is the half life for grading power calculations?",4, fileDescriptor=logFile)
		params.compensationFactor=getNum("What compensation factor for grader deviations (0-1)?",1,[0,1], fileDescriptor=logFile)
		if (params.compensationFactor>0):
			params.maxCompensationFraction=getNum("What is the max fractional amount of a score that can be compensated (0-1)?",defaultVal=0.2,limits=[0,1], fileDescriptor=logFile)
		else:
			params.maxCompensationFraction=0;
	logFile.close()
	with open(status['dataDir'] +status['prefix'] + 'parameters.pkl', 'wb') as handle:
		pickle.dump(params, handle, protocol=pickle.HIGHEST_PROTOCOL)
	status["gotParameters"]=True
	return params

######################################
# save data to a log file
def log(msg, display=True, fileName=None):
	if fileName==None:
		fileName=status['prefix']+".log"
	theFile=status['dataDir'] + fileName
	if display:
		print(msg, end ="")
	f = open(theFile, "a")
	f.write("----" + str(datetime.now()) + "----\n")
	f.write(msg) 
	f.write("\n\n") 
	f.close()


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
			try:
				points=student.points[assignment.id]
				grades=student.grades[assignment.id]
				creationGrade.append(grades['creation'])
				reviewGrade.append(grades['review'])
				rawTotal.append(grades['total'])
				curvedTotal.append(points['curvedTotal'])
			except:
				pass
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
		axis.hist(marks, bins = [0, 10, 20, 30, 40,50, 60, 70, 80, 90, 100])
		plt.title('Curved grades\n\n',
				  fontweight ="bold")
		# Displaying the graph
		plt.show(block=False)
	if text:
		print("Creation average is %.1f with stdev of %.1f" % (np.average(creationGrade),np.std(creationGrade)) )	
		print("Review average is %.1f with stdev of %.1f" % (np.average(reviewGrade),np.std(reviewGrade)) )	
		print("Raw total average is %.1f with stdev of %.1f" % (np.average(rawTotal),np.std(rawTotal)) )	
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
			header+='"' + criteriaDescription[cid] + '"' + delimiter #"LO" + str(cid) + delimiter
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
					'"' + student.reviewGradeExplanation + '"'
					) + '\n'
			else:
				line+= ',\n'
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
		print("\nCurrent graders are ")
		for g in listOfGraders:
			print("\t"+g.name)
	else:
		print("The class has no graders.")
######################################
# Select students to be assigned as graders
def assignGraders():
	listOfGraders=[s for s in students if s.role=='grader']
	viewGraders()
	if confirm("is this ok? "):
		######### Save student data for future sessions #########	
		with open(status['dataDir'] +status['prefix'] + 'students.pkl', 'wb') as handle:
			pickle.dump(students, handle, protocol=pickle.HIGHEST_PROTOCOL)
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
	except:
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
	sortedStudents=sorted(students, key = lambda x : x.getDeviation(cid), reverse=True) 
	if theStudent=="all":
		print("--Easiest graders--")
		for (i,student) in enumerate(sortedStudents):
			if student.role == 'student':
				print(str(i+1)+")\t" + student.name + " %.2f" % student.getDeviation(cid))
			elif student.role == 'grader':
				print(str(i+1)+")\t" + student.name + " %.2f  (grader)" % student.getDeviation(cid))
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
		except:
			print("error messaging " ,student.name, ".  Perhaps the student dropped." )
		if display:
			print("messaging " +  student.name)
			
######################################
# Read a CSV file and return the data as an array
def readCSV(fileName=None):
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
		return	(confirmationResponse == 'ok')
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
		except:
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
# List all objects in an array and prompt the user to select one.  
# Once they confirm their choice it will be returned

def select(objArray, prompt="Choose one"):
	for i,obj in enumerate(objArray):
		print(i , obj)

	confirmed=False
	while not confirmed:	
		response=input(prompt + ": ")
		selection=int(response)
		response = input("type 'ok' to confirm or choose a new value" + str(objArray[selection]) + ": " ) 
		confirmed = (response == 'ok')
	return objArray[selection]

######################################
# Take an array and return a shuffled version of it 
def randmoize(theArray):
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
def inputWithTimeout(prompt, timeout):
	import signal, threading
	prompt=formatWithBoldOptions(prompt)
	stopFlag=False
	class Countdown:
		def __init__(self):
			self._running=True
		
		def terminate(self):
			self._running = False
	
		def run(self,n, prompt):
			msg=" "*len(str(n)) + " " + prompt + ": "
			for i in range(n,0,-1):
				if self._running:
					msg1= reverseText(str(i))  +msg[len(str(i)):]
					print("\r"+msg1, end="")
					for j in range(100):
						if self._running:
							time.sleep(0.01)
				printLine("",False)
			print("\r",end="")
			
	def alarm_handler(signum, frame):
		raise TimeoutExpired
	msg=" "*len(str(timeout)) + " " + prompt + ": "
	cnt=Countdown()
	new_thread = threading.Thread(target=cnt.run, args=(timeout,prompt))
	new_thread.start()	
	signal.signal(signal.SIGALRM, alarm_handler)
	signal.alarm(timeout) # produce SIGALRM in `timeout` seconds
	try:
		val= input()
		cnt.terminate()
		printLine("",False)
		print("\r", end="")
		time.sleep(0.1)
		signal.alarm(0)
		return val
	except:
		printLine("",False)
		print("\r", end="")
	signal.alarm(0)
	cnt.terminate()
	time.sleep(0.1)
	return None
	
######################################
# print a line by printing white space
def printLine(msg="", newLine=True):
	size=os.get_terminal_size()
	cols=size.columns
	if newLine:
		print("\r{: <{width}}".format(msg, width=cols))		
	else:
		print("\r{: <{width}}".format(msg, width=cols),end="")	

######################################
# clear a list without redefining it.  Allows it to be kept in global scope
def clearList(lst):
	if	type(lst) == list:
		while lst:
			lst.pop()
	elif type(lst) ==dict:
		while lst:
			lst.popitem()

# def detectKeyPress(key=' ',duration=1):
# 	import keyboard, time
# 	start=time.time()
# 	keypress=False
# 	while time.time()-start < duration:
# 		keypress = keypress or keyboard.is_pressed(key)
# 	return keypress