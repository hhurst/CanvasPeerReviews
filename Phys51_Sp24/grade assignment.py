#################  Set up where to the environment  #################
from path_info import * 			# Set up where to find the relevant files
from CanvasPeerReviews import *		# the main module for managing peer reviews

#################  Get the data for the course  #################
students, graded_assignments, lastAssignment = initialize(CANVAS_URL, TOKEN, COURSE_ID, DATADIRECTORY)

#################  Get relevant parameters assignment  #################
params=getParameters()
# if no assignments have yet been graded then prompt for graders
if len([g for g in graded_assignments.values() if g.graded])==0: 
	assignGraders()
else:
	viewGraders()
	val=inputWithTimeout("(g) update grader list",3)
	if (val=='g'):
		assignGraders()
activeAssignment=lastAssignment
if activeAssignment.graded:
	activeAssignment=chooseAssignment(requireConfirmation=False)

print("The following point distribution will be used for "+activeAssignment.name+":")
for cid in activeAssignment.criteria_ids():
	multiplier=params.pointsForCid(cid, activeAssignment)
	print("\t" + str(multiplier)+ " points for '"+   criteriaDescription[cid] + "'")
if not confirm():
	setPoints(lastAssignment)
	val=input("Enter any additional comments to post with the grades: ").strip()
	if val!="":
		utilities.additionalGradingComment=val+"\n\n"

# Get creations and reviews
getStudentWork(activeAssignment)

	
print(activeAssignment.name + " is done with peer reviewing \nlet's make it the active assignment.")
val=inputWithTimeout("Will look for regrades from previous weeks.  (s) to skip",5)
if val!='s':
	regrade()
#val=inputWithTimeout("Will calibrate student graders.  (s) to skip",5)
#if val!='s':
calibrate()

#overrideDefaultPoints(activeAssignment)

val=inputWithTimeout("using '" + activeAssignment.reviewCurve + "' for review scores.  (c) to change",5)
if val=='c':
	activeAssignment.reviewCurve=confirm(msg="Enter curve as a function of rms: ", requireResponse=True)

acceptedCurve=False
while not acceptedCurve:
	curve=input(f'Enter an expression that takes a raw score x and returns a curved score (out of {int(activeAssignment.points_possible)}), for instance "round({activeAssignment.points_possible/2}+x/2)": ')
	if curve=="":
		curve="x"
	activeAssignment.curve=curve
	grade(activeAssignment)	
	getStatistics(activeAssignment, hist=True)
	acceptedCurve=confirm("Are thes statistics ok?")
log("Accepted " + activeAssignment.curve + " as the curve for " +  activeAssignment.name)

print("\nGrades saved to file 'scores for " + activeAssignment.name + "'")
exportGrades(activeAssignment)
print("Grades exported")
print()
if confirm("Post grades on canvas?", False):
	postGrades(activeAssignment)
print("\nGrading Power Rankings")
gradingPowerRanking()
print("\nGrading Deviation Rankings")
gradingDeviationRanking()
finish(True)