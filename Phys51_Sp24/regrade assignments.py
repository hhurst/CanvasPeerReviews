#################  Set up where to the environment  #################
from path_info import * 			# Set up where to find the relevant files
from CanvasPeerReviews import *		# the main module for managing peer reviews

#################  Get the data for the course  #################
students, graded_assignments, lastAssignment = initialize(CANVAS_URL, TOKEN, COURSE_ID, DATADIRECTORY)

#################  Get relevant parameters assignment  #################
params=getParameters()

#viewGraders()
#val=inputWithTimeout("(g) update grader list",3)
#if (val=='g'):
#	assignGraders()
if lastAssignment.graded:
	activeAssignment=lastAssignment
else: 
	# get the most recent assignment that was graded but not yet regraded
	defaultAssignment=lastAssignment
	defaultPrompt="last assignment"
	for key in graded_assignments:
		if graded_assignments[key].graded and not graded_assignments[key].regradesCompleted:
			defaultAssignment=graded_assignments[key]
			defaultPrompt="last unregraded assignment"
	activeAssignment=chooseAssignment(requireConfirmation=False, allowAll=True, defaultAssignment=defaultAssignment,defaultPrompt=defaultPrompt )

#regrade
if not isinstance(activeAssignment,str):
	regrade(activeAssignment) # only do this if the active assignment is an assignment (As opposed to the string "all")
if confirm("Shall we regrade all unfinalized assignments?"):
	regrade()
finish(True)

