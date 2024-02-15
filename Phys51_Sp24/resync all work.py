#################  Set up where to the environment  #################
from path_info import * 			# Set up where to find the relevant files
from CanvasPeerReviews import *		# the main module for managing peer reviews

#################  Get the data for the course  #################
students, graded_assignments, lastAssignment = initialize(CANVAS_URL, TOKEN, COURSE_ID, DATADIRECTORY, update=True)

#################  Get relevant parameters assignment  #################
params=getParameters()
print("Syncing all work, reviews and assignments that are past due.")

for s in students:
	s.comparisons=dict()

for key in graded_assignments:
	ga=graded_assignments[key]
	#if key != 'last' and ga.secondsPastDue()>0 and ga.published and ga.graded:
	if ga.published and ga.secondsPastDue()>0:
		print(f"Getting work on {ga.name}")
		getStudentWork(ga)
		cs=[c for c in creations if c.author_id in studentsById] # don't consider any submission by students we don't know about
		resyncReviews(ga,cs)
		#allowPrinting(False)
		calibrate(endDate=ga.date)
		grade(ga)
		allowPrinting(True)
utilities.dataToSave['students']=True
utilities.dataToSave['reviews']=True
utilities.dataToSave['assignments']=True
finish(True)