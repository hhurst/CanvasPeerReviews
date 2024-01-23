#################  Set up where to the environment  #################
from path_info import * 			# Set up where to find the relevant files
from CanvasPeerReviews import *		# the main module for managing peer reviews

#################  Get the data for the course  #################
students, graded_assignments, lastAssignment = initialize(CANVAS_URL, TOKEN, COURSE_ID, DATADIRECTORY)

#################  Get relevant parameters assignment  #################
params=getParameters()

while True:
	val=input("\nstudent name (or partial name) to inspect (capitalized to deanonymoize)\nreview number for more info, or <enter> for a list of students: ")
	printLine(line=True)
	try:
		key=int(val)
		review=reviewsById[key]
		author=studentsById[review.author_id]
		ga=graded_assignments[review.assignment_id]
		#author_id=review.author_id
		#assignment_id=review.assignment_id
		#submission_id=review.submission_id
		if anonymous:
			print(f"\nReview {key} on '{ga.name}'\033[1m reviewed by {studentsById[review.reviewer_id].name}\033[0m")
		else:
			print(f"\nReview {key} on '{ga.name}'\n\033[1msubmission by {author.name} reviewed by {studentsById[review.reviewer_id].name}\033[0m")
		for url in review.urls:
			print(url)
		print()
		profReviewed=False
		review.getComments()
		try:
			pr=[pr for pr in professorsReviews[review.assignment_id] if pr.submission_id==review.submission_id][0]
			otherScore=pr.scores
			profReviewed=True
			pr.getComments()
			print(f'{"Criteria":<30}{studentsById[review.reviewer_id].name.split(" ")[0]:15}{"Prof":<15}')
		except IndexError:
			otherPoints=author.pointsByCriteria[review.assignment_id]
			otherScore=dict()
			for cid in otherPoints:
				otherScore[cid]=otherPoints[cid]*ga.criteria_points(cid)/params.pointsForCid(cid, ga) 
			print(f'{"Criteria":<30}{studentsById[review.reviewer_id].name.split(" ")[0]:<15}{"Average":<15}')
		for cid in review.scores:
			print(f'{criteriaDescription[cid]:<30}{review.scores[cid]:<15}{otherScore[cid]:.1f}')
		if profReviewed and pr.commented:
			print("\nProfessor's comments:\n" +Fore.BLUE+ pr.allComments + Style.RESET_ALL)
			if review.commented:
				print(f"\n{studentsById[review.reviewer_id].name.split(' ')[0]}'s comments:\n {Fore.GREEN}{review.allComments}{Style.RESET_ALL}")		
	except ValueError:
		anonymous=(val!=val.upper() and val!="")
		s=selectStudentByName(val)
		print("\033[1mReport for " + s.name + "\033[0m")
		reviewsGiven=[reviewsById[key] for key in reviewsById if reviewsById[key].reviewer_id == s.id]
		#for key in reviewsGiven:
		for review in reviewsGiven:
			try:
				a=studentsById[review.author_id]
				ga=[graded_assignments[key] for key in graded_assignments if key == review.assignment_id][0]
				reviewedByProfessor=(review.assignment_id in professorsReviews) and (review.author_id in [pr.author_id for pr in professorsReviews[review.assignment_id]])	
				awardedPoints=a.pointsByCriteria[review.assignment_id]
				reviewGradeFunc= eval('lambda x:' + graded_assignments[review.assignment_id].reviewCurve.replace('rms','x'))
				givenPoints=review.scores
				#print(f'Review of {a.name} on {graded_assignments[review.assignment_id].name}:')
				if reviewedByProfessor:
					print(Fore.BLUE, end="")
				if anonymous:
					print(f'\nReview {review.id} of author id {a.id} on {graded_assignments[review.assignment_id].name}:')
				else:
					print(f'\nReview {review.id} of {a.name} on {graded_assignments[review.assignment_id].name}:')
				for cid in review.scores:
					try:	
						dev=abs(awardedPoints[cid]*ga.criteria_points(cid)/params.pointsForCid(cid, ga) - givenPoints[cid]) 
						print(f'\t{criteriaDescription[cid]:<30} had a deviation of {round(dev,1)} for a grade of {round(reviewGradeFunc(dev/5))}')
					except:
						print(f'\t{criteriaDescription[cid]:<30} had a deviation of ??? for a grade of ???')
			except KeyError:
				print(f"Key error - perhaps {graded_assignments[review.assignment_id].name} hasn't been graded yet")	
			except AttributeError:
				pass
			print(Style.RESET_ALL, end="")
		print("\033[1mThe above report is for " + s.name + "\033[0m")
