#################  Set up where to the environment  #################
from path_info import * 			# Set up where to find the relevant files
from CanvasPeerReviews import *		# the main module for managing peer reviews

#################  Get the data for the course  #################
students, graded_assignments, lastAssignment = initialize(CANVAS_URL, TOKEN, COURSE_ID, DATADIRECTORY)
#################  Get relevant parameters assignment  #################
params=getParameters()

# Get creations and reviews
#activeAssignment=chooseAssignment(requireConfirmation=False,  timeout=5, defaultAssignment=lastAssignment)
activeAssignment=chooseAssignment(requireConfirmation=False, timeout=5, defaultAssignment=lastAssignment)
getStudentWork(activeAssignment)

#resyncReviews(activeAssignment,creations) # this slows things down a lot, it should only be necessary if you have manually assigned reviews from the canvas web interface

# Count all the peer reviews that were assigned (for this assignment)
assignedAssessmentsToStudents,assignedAssessmentsToGraders = 0,0
for student in students:
	try:
		if student.role == 'student':
			assignedAssessmentsToStudents+=student.numberOfReviewsAssignedOnAssignment(activeAssignment)
		else:
			assignedAssessmentsToGraders+=student.numberOfReviewsAssignedOnAssignment(activeAssignment)
	except:
		pass
studentsWithoutSubmissions=[s for s in students if s.role=='student' and not activeAssignment.id in s.creations]

assignedAssessments=assignedAssessmentsToGraders+assignedAssessmentsToStudents	
	
# Count how many of the assigned peer reviews have been completed		
completedAssessmentsByGraders, completedAssessmentsByStudents, completedAssessmentsByInstructor = 0,0,0
graderIDs=[s.id for s in students if s.role=='grader']
processedReviewIds=dict()
for key in reviewsByCreationId:
	for review in reviewsByCreationId[key].values():
		if review.creation.assignment_id == activeAssignment.id and review.id not in processedReviewIds:
			processedReviewIds[review.id]=True
			if (review.review_type=='grading' ):
				completedAssessmentsByInstructor+=1
			elif (review.review_type=='peer_review' ):
				if review.reviewer_id in graderIDs:
					completedAssessmentsByGraders+=1
				else:
					completedAssessmentsByStudents+=1

# make a list of all the submitted reviews as well as a list of ones that were submitted before the rubric was completely filled in
reviews=[]
for key in utilities.reviewsByCreationId:
	reviews.append(list(utilities.reviewsByCreationId[key].values())[0])
incompleteReviews=[]
for review in reviews:
	if review.creation.assignment_id == activeAssignment.id:
		for d in review.data:
			try:
				temp=d['points']
			except:
				if review.reviewer_id in studentsById and review.author_id in studentsById:
					if  not findInLog(review.fingerprint()):
						incompleteReviews.append(review)
					else:
						print("ignoring incomplete review [" + review.fingerprint() + "]  because it has already been reset")


completedAssessments=completedAssessmentsByGraders+completedAssessmentsByStudents
unreviewedCreations=checkForUnreviewed(activeAssignment, openPage=False) #get the number of incomplete reviews

print("\n")
print("\t"+str(len(studentsWithoutSubmissions)) + " students without a submission")
print("\t"+str(len(unreviewedCreations))+ " creations are unreviewed")
print("\t"+str(completedAssessmentsByInstructor) + " assignments graded by instructor")
if assignedAssessmentsToStudents>0:
	print("\t"+str(int(100*completedAssessmentsByStudents/assignedAssessmentsToStudents)) + "% of reviews by students have been completed")
if assignedAssessmentsToGraders>0:
	print("\t"+str(int(100*completedAssessmentsByGraders/assignedAssessmentsToGraders)) + "% of reviews by graders have been completed")
print("\t"+str(len(incompleteReviews)) + " incomplete reviews")
print("")
# make a list of students who havent' started their peer reviews yet
delinquentReviewers=[s for s in students if s.role=='student' and s.numberOfReviewsGivenOnAssignment(activeAssignment.id)==0 and activeAssignment.id in s.creations]
print("No reviews by", len(delinquentReviewers),"students")


def showDelinquentStudents():
	for student in delinquentReviewers:
		print("\t" + student.name)	
	if confirm("Shall I message these students to remind them?"):
		msg=processTemplate(student,activeAssignment,"reminder about peer reviews")
		msg=confirmText(msg)
		message(delinquentReviewers, body=msg, subject='Reminder to complete your peer reviews', display=True)
		print("Messages sent")
	else:
		print("OK, no messages sent")


#offer to reset any incomplete reviews and message the reviewers to let them know to redo them
ReviewCount=0
for review in incompleteReviews:
	if not findInLog(review.fingerprint()):
		for d in review.data:
			reviewerID=review.reviewer_id
			reviewer=studentsById[reviewerID]
			authorName=studentsById[review.author_id].name
			print("Incomplete review of " + authorName +" by " + reviewer.name)
			val=input("(r) reset review or (i) ignore incomplete review: ")
			if (val=='r'):
				msg1="Hi "+reviewer.name.split(" ")[0]+",  I  noticed one of your reviews was incomplete - likely because you hit 'save' before entering all of the data.  Since Canvas doesn't have a way to go back and finish a 'saved' review, I have deleted it and reassigned it so you can submit a complete review.  Here is what you had entered initially:\n\n"
				msg1+=reviewSummary(review)
				msg=confirmText(msg1)
				#find the creation that has a failed review
				c1=[c for c in creations if c.id == review.submission_id][0]
				#delete the failed review
				c1.delete_submission_peer_review(reviewerID)
				#reassign the review
				c1.create_submission_peer_review(reviewerID)
				#log it
				log("reset review [" + review.fingerprint() + "]")
				# need to send a message with text msg
				message(reviewer, body=msg, subject='Incomplete peer review', display=False)
				#canvas.create_conversation(recipients=str(reviewerID), body=msg, subject='Incomplete peer review')
				ReviewCount+=1
			break
	else:
		print("skipping in complete review [" + review.fingerprint() + "]  because it has already been reset")
if len(incompleteReviews)==0:
	print("No incomplete reviews found")
elif ReviewCount>0:
	print(" " + str(ReviewCount) + " incomplete reviews")
else:
	print("Ignored " + str(len(incompleteReviews)) + " incomplete reviews")
unreviewedCreations=checkForUnreviewed(activeAssignment, openPage=True)  #open a web page with links to all of the incomplete reviews.
#offer to message students who haven't yet started their reviews

#val=inputWithTimeout("(s) show students who haven't done any reviews", 60)
#if confirm("\nShow students who haven't done any reviews? "):
if confirm("Show students who haven't yet done a review?"):
	showDelinquentStudents()
	endMessage="Done!"
else:
	endMessage="type 'showDelinquentStudents()' to show and/or message students who haven't yet completed any reviews"
print(endMessage)
finish(True)
	
