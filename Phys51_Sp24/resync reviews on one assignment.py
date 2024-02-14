#################  Set up where to the environment  #################
from path_info import * 			# Set up where to find the relevant files
from CanvasPeerReviews import *		# the main module for managing peer reviews

#################  Get the data for the course  #################
students, graded_assignments, lastAssignment = initialize(CANVAS_URL, TOKEN, COURSE_ID, DATADIRECTORY)
#################  Get relevant parameters assignment  #################
params=getParameters()

# Get creations and reviews
activeAssignment=chooseAssignment(requireConfirmation=False,  timeout=5, defaultAssignment=lastAssignment)
getStudentWork(activeAssignment)
resyncReviews(activeAssignment,creations) # this slows things down a lot, it should only be necessary if you have manually assigned reviews from the canvas web interface
utilities.dataToSave['students']=True
finish(True)