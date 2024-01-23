#################  Set up where to the environment  #################
from path_info import * 			# Set up where to find the relevant files
from CanvasPeerReviews import *		# the main module for managing peer reviews

#################  Get the data for the course  #################
students, graded_assignments, lastAssignment = initialize(CANVAS_URL, TOKEN, COURSE_ID, DATADIRECTORY)

#################  Get relevant parameters assignment  #################
params=getParameters()

activeAssignment=chooseAssignment(requireConfirmation=False)
calibrate()
while True:
	#student=select(students,property="name", requireConfirmation=False)
	printLine(line=True)
	theName=input("Enter the name (or partial name) of the student, or 'a' to change assignment: ")
	if theName=='a':
		activeAssignment=chooseAssignment(requireConfirmation=False)
	else:
		student=selectStudentByName(theName)

	print("Report on grades received by " + student.name + " on " + activeAssignment.name) 
	print("score on each category is (Σ weight* (points+compensations))/Σweights\n")
	student.pointsOnAssignment(activeAssignment)

	print("")
	print("Report on reviews given by " + student.name + " compared to other reviews on " + activeAssignment.name ) 

	student.gradingReport()

	percentile=gradingPowerRanking(student, percentile=True)
	print("Student is in the " + str(percentile)+ "th percentile as a grader")
	