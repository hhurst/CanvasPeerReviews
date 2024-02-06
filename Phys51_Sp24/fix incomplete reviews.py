from credentials import *
import sys, os
sys.path.insert(0, "/Users/hilary/PycharmProjects/CanvasPeerReviewsTop/CanvasPeerReviews")
from path_info import *
from CanvasPeerReviews import *


#################  course info  #################
canvas = Canvas(CANVAS_URL, TOKEN)
course = canvas.get_course(COURSE_ID)
students, graded_assignments, lastAssignment = initialize(CANVAS_URL, TOKEN, COURSE_ID)

#################  Get relevant parameters assignment  #################
params=getParameters()
#assignGraders()

# Get creations and reviews
getStudentWork()
activeAssignment=lastAssignment

currentCreations=[c for c in creations if c.assignment_id == activeAssignment.id]
criteriaDescription=dict()

def reviewSummary(assessment):
	global criteriaDescription
	print("Review of " + str(assessment['artifact_id']) + " by " +studentsById[assessment['assessor_id']].name+ "\n")
	msg=""
	for d in assessment['data']:
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
	return msg
			
			

for criteria in activeAssignment.rubric:
	criteriaDescription[criteria['id']]=criteria['description']



rubrics=course.get_rubrics()
incompleteReviewCount=0
resetReviewCount=0
for rubric in rubrics:
	rubric=course.get_rubric(rubric.id,include='assessments', style='full')
	if hasattr(rubric, 'assessments'):
		for assessment in rubric.assessments:
			for d in assessment['data']:
				try:
					temp=d['points']
				except:
					print("error")
					de=d
					ae=assessment
					reviewerID=ae['assessor_id']
					reviewer=studentsById[reviewerID]
					#listOfAuthorNames=[studentsById[c.author_id].name for c in creations if c.id==ae['artifact_id']]
					listOfAuthorNames=[studentsById[creationsById[ae['artifact_id']].author_id].name]
					if len(listOfAuthorNames)>0:
						authorName=listOfAuthorNames[0]
						print("Incomplete review of " + authorName +" by " + reviewer.name)
						msg="Hi "+reviewer.name.split(" ")[0]+",  I  noticed one of your reviews was incomplete - likely because you hit 'save' before entering all of the data.  Since Canvas doesn't have a way to go back and finish a 'saved' review, I have deleted it and reassigned it so you can submit a complete review.  Here is what you had entered initially:\n\n"
						msg+=reviewSummary(ae)
						print(msg)
						val=input("(r) reset review or (i) ignore incomplete review: ")
						incompleteReviewCount+=1
						if (val=='r'):
							#find the creation that has a failed review
							c1=[c for c in creations if c.id == ae['artifact_id']][0]
							#delete the failed review
							c1.delete_submission_peer_review(reviewerID)
							#reassign the review
							c1.create_submission_peer_review(reviewerID)
							# need to send a message with text msg
							canvas.create_conversation(recipients=str(reviewerID), body=msg, subject='Incomplete peer review')
							resetReviewCount+=1
						break
					else:
						print("Incomplete review found but don't know the author of creation with id " + str(ae['artifact_id']))
if incompleteReviewCount==0:
	print("No incomplete reviews found")
elif resetReviewCount>0:
	print("Reset " + str(resetReviewCount) + " incomplete reviews")
else:
	print("Ignored " + str(incompleteReviewCount) + " incomplete reviews")
