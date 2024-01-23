#################  Set up where to the environment  #################
from path_info import * 			# Set up where to find the relevant files
from CanvasPeerReviews import *		# the main module for managing peer reviews

#################  Get the data for the course  #################
students, graded_assignments, lastAssignment = initialize(CANVAS_URL, TOKEN, COURSE_ID, DATADIRECTORY)

#################  Get relevant parameters assignment  #################
params=getParameters()
activeAssignment=lastAssignment
assignments = utilities.course.get_assignments()
now=datetime.utcnow().replace(tzinfo=pytz.UTC)
assignmentsToCheck=[]

namesAndDays=[]
for assignment in assignments:
	try:
		if assignment.published and (now-assignment.due_at_date).total_seconds() > 0 and assignment.has_submitted_submissions:
			daysSinceDue=(now-assignment.due_at_date).total_seconds()/(24*3600)
			namesAndDays.append([daysSinceDue, assignment.name])
	except:
		pass
sortedNamesAndDays=sorted(namesAndDays,key=lambda x: -x[0])
for nameAndDays in sortedNamesAndDays:
	print(f"{int(round(nameAndDays[0],0))}: {nameAndDays[1]}")
	


daysToConsider=None
while daysToConsider==None:
	try:
		print("")
		print("Search for comments on assignments due in the last how many days? ")
		val=inputWithTimeout("or 's' to select a single assingment ", 10,7)
		daysToConsider=float(val)
		print(f"Will look for comments on assignments due in last {val} days")
	except ValueError:
		if val.lower()=='s':
			daysToConsider=0
			activeAssignment=chooseAssignment()
			print(f"Will look for comments on {activeAssignment.name}")
			assignmentsToCheck.append(activeAssignment)
for i,assignment in enumerate(assignments):
	try:
		if assignment.published and (now-assignment.due_at_date).total_seconds() >0:
			if daysToConsider!=0 and (now-assignment.due_at_date).total_seconds() <daysToConsider*24*3600:
				assignmentsToCheck.append(assignment)
				#print(i,assignment.name)
	except:
		pass

#if daysToConsider==0:
#	val=int(input("Choose assignment: "))
#	activeAssignment=assignments[val]

def getRecentCommentOnAssignment(assignment):
	if not assignment.published:
		print(f"{assignment.name} is not published - not looking for comments")
		return
	# Get creations and reviews
	submissions=assignment.get_submissions()
	fileName=status['dataDir'] + assignment.name + "_comments.html"
	f = open(fileName, "w")
	f.write("<html><head><title>Author comments on " + assignment.name + " </title><style>\n")
	f.write("a {text-decoration:none}\n")
	f.write("</style><meta http-equiv='Content-Type' content='text/html; charset=utf-16'></head><body>\n")
	f.write("<h3>Author comments on "+assignment.name+"</h3>\n<table>\n")
	printedResult=False
	
	from html import escape
	commentsToProcess=[]
	for i,c in enumerate(submissions):
		print("\r" +assignment.name + ": Checking creation " + str(i) + "/" + str(len(students)), end="", flush=True)
		hideCursor()
		allCreationComments=c.edit().submission_comments
		for comment in allCreationComments:
			commentTime= datetime.strptime(comment['created_at'], "%Y-%m-%dT%H:%M:%SZ")
			thisDelta=datetime.utcnow()-commentTime
			delta=thisDelta.total_seconds() #age of comment in seconds
			previewUrl=c.preview_url.split("?")[0]
			speedGraderURL=previewUrl.replace("assignments/","gradebook/speed_grader?assignment_id=").replace("/submissions/", "&student_id=").replace("?version=1","")
			c.author_id=c.user_id
			if (comment['author']['id'] == c.author_id):
				replied=False
				for otherComment in allCreationComments:
					otherCommentTime=datetime.strptime(otherComment['created_at'], "%Y-%m-%dT%H:%M:%SZ")
					thisDelta=otherCommentTime-commentTime
					delta=thisDelta.total_seconds()
					if (delta>0 and otherComment['author']['id'] not in studentsById ):
						replied = True
				if not replied:
					if not printedResult:
						print("\033[1m" + "Author comments for " + assignment.name + "\033[0m")
						printedResult=True
					printLine(msg="", newLine=False)
					print("\r"+comment['author']['display_name'] + " said: \n" + Fore.GREEN +  Style.BRIGHT + comment['comment'] +  Style.RESET_ALL + "\n")
					commentsToProcess.append({'creation': c, 'comment': comment})
					f.write("<tr><td>" + " <img src='" +comment['author']['avatar_image_url']+ "'><br>\n" + comment['author']['display_name'] +"</td>")
					f.write("<td> " + comment['author']['display_name'].split(" ")[0] + " said: <a href='"+ speedGraderURL +"'>" + escape(comment['comment']).replace("’","'") + "</a></td></tr>")
	f.write("</table></body></html>\n")
	f.close()
	if not printedResult:
		print("\r\033[1m" + "No new author comments for " + assignment.name + "\033[0m")
	if len(commentsToProcess)>0:
		subprocess.call(('open', fileName))
	else:
		os.remove(fileName)
	showCursor()
	printLine(msg="", newLine=False)
	val=""
	for i,commentData in enumerate(commentsToProcess):
		printLine(line=True)
		comment=commentData['comment']
		c=commentData['creation']
		print(str(i+1) + "/" + str(len(commentsToProcess)) + "\t"+ comment['author']['display_name'] + " said: \n" + Fore.GREEN+  Style.BRIGHT + comment['comment'] +  Style.RESET_ALL)
		#print("\n" + Fore.MAGENTA +speedGraderURL + Style.RESET_ALL)
		proceed=False
		while not proceed:
			if val!='S':
				val=input("\n(c) to view context, (s) to skip, (S) to skip all or type a response:\n").strip()
			if val.lower()=="c":
				allCommentsForThisSubmission=c.edit().submission_comments
				for thisComment in allCommentsForThisSubmission:
					if thisComment['author']['id'] not in studentsById:
						color=Fore.BLUE +  Style.BRIGHT
					else:
						if (thisComment['author']['id'] == c.author_id):
							color=Fore.GREEN +  Style.BRIGHT
						else:
							color=Fore.MAGENTA +  Style.BRIGHT
					print("\n\n" + thisComment['author']['display_name']+ " said:\n"+ color + thisComment['comment'] + Style.RESET_ALL)
			elif val.lower()=="s" or val=="":
				print("Skipping")
				proceed=True
			else:
				print("Posting comment...")
				c.edit(comment={'text_comment':val})
				proceed=True

for activeAssignment in assignmentsToCheck:
	#print(f"Checking {activeAssignment.name} for comments:" )
	getRecentCommentOnAssignment(activeAssignment)