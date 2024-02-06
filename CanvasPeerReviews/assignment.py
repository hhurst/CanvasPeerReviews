from datetime import datetime, timedelta
import pytz

class GradedAssignment:
	def __init__(self, assignment):	
		if hasattr(assignment, 'rubric'):
			for outcome in assignment.rubric:
				if not 'id' in outcome:
					outcome['id']=None
				if not 'title' in outcome:
					outcome['title']=None
		self.__dict__ = assignment.__dict__.copy() 
		self.graded = False 
		self.gradesPosted = False 
		self.regraded = False 
		self.peer_reviews_assigned = False
		self.get_peer_reviews=assignment.get_peer_reviews
		self.get_submissions=assignment.get_submissions
		self.multiplier=dict()
		self.curve='x'
		self.reviewCurve='max(0,min(100, 120*(1-1.1*rms)))'
		self.regradesCompleted=False
		self.date=self.getDate(assignment)
		self.pointsByCidOverride=dict()
		self.reviewScoreMethod="calibrated grading"
		self.includeInCalibrations=True
		self.solutionsUrl=None

	def sync(self, updatedAssignment):
		# if the due date has changed on canvas this updates that
		# records that change.
		if updatedAssignment.id == self.id:
			self.__dict__.update(updatedAssignment.__dict__)
			self.date=self.getDate(updatedAssignment)
	
	def setReviewScoringMethod(self):
		# There are three ways that peer reviews can be scores:
		#
		# 'Calibrated Grading' compares scores assigned by the reviewer
		# to those given by others.  The closer the scores align the
		# higher the review score.
		#
		# 'percent complete' simply gives a score based on what percent
		# of the assigned reviews were completed.  If all reviews
		# were completed a score of 100% is given
		#
		# 'ignore' will not grade the peer reviews but will instead 
		# copy the creation score to the review score.
		print()
		try:
			currentMethod =  self.reviewScoreMethod
		except:
			self.reviewScoreMethod = "calibrated grading"
			currentMethod =  self.reviewScoreMethod
		methods=["calibrated grading","percent completed", "ignore"]
		for i, method in enumerate(methods):
			if self.reviewScoreMethod == method:
				print(f"{i+1}) {method} <---- current value")
			else:
				print(f"{i+1}) {method}")
		val=0
		while val<1 or val>len(methods):
			val=input("Which method do you want to use? ")
			try:
				val=int(val)
			except:
				val=0
		self.reviewScoreMethod=methods[val-1]
		print("Set " + self.name + " to use '" + self.reviewScoreMethod + "' method for review grades ")
			
	
	def secondsPastDue(self):
		# return the number of seconds past the due date for the assignment
		now=datetime.utcnow().replace(tzinfo=pytz.UTC)
		try:
			delta=now-self.date
			return delta.total_seconds()
		except:
			return -99999999
	
	def getDate(self, updatedAssignment=None):
		# return the due date of the assignment.  If there are 
		# multiple due dates for different students it returns the
		# last of the possible dates.
		if updatedAssignment==None:
			updatedAssignment=self
		d=None
		try:
			d=updatedAssignment.due_at_date
			for o in self.get_overrides():
				do=o.due_at_date
				if (do>d):
					d=do
		except AttributeError:
			pass
		return d
										
	def countPeerReviews(self):
		# returns the number of peer reviews that have been assigned
		# in total for this assignment by polling canvas for a list
		# of all peer reviews and counting them.
		peer_reviews=self.get_peer_reviews()
		cnt=0		
		for peer_review in peer_reviews:
			cnt+=1
		return cnt
		
		
	def criteria_points(self, cid):
		# points defined by the criteria rubric in canvas
		# if for example a criteria is set to 5 points in canvas
		# so that students can give a score of 0-5, but the criteria
		# is meant to account for 50 points as set by setPoints(), 
		# then the raw score recorded from canvas would be divided
		#by 5 and multiplied by 50.  
		total=0
		cnt=0
		for criteria in self.rubric:
			if "id" in criteria or "description" in criteria:
				total+=criteria['points']
				cnt+=1
				if criteria['id'] == cid or criteria['description']==cid:
					return criteria['points']
			else:
				if cid == None:
					return criteria['points']
		if cid==0:
			return 1.0*total/cnt
		return 0

	#points that the score should be scaled to for grading
	def setPoints(self, defaults={}):
		# this prompts the user for how many points (typically out of 100) each criteria 
		# should be worth.  If not defined the course defaults set in the
		# parameters object will be used when grading this assignment
		print("Set an override to the defaul points on " + self.name + ":\n")
		for criteria in self.rubric:
			cid=criteria['description']
			defaultVal=self.criteria_points(cid)
			if cid in self.multiplier:
				defaultVal=self.multiplier[cid]
			elif cid in defaults:
				defaultVal=defaults[cid]
			val=input("How many points (out of 100) for '" + criteria['description'] + "' criteria [" +str(defaultVal)+ "]? ")
			try:
				val=float(val)
			except:
				val=defaultVal
			self.multiplier[cid]=val

	def pointsForCid(self, cid):
		# this returns how many points (typically out of 100) a given criteria 
		# should be worth.  The defaults for this are defined in the course
		# parameters object, but if they are defined here it will override the
		# course defaults when grading this assignment
		if cid in self.multiplier:
			return self.multiplier[cid]
		return "default"	
			
	def criteria_ids(self):
		# return a list of ids for the various grading criteria for this assignment	
		cids=[]
		for criteria in self.rubric:
			try:
				cids.append(criteria['description'])
			except:
				cids.append(None)
		return cids

	def criteria_descriptions(self, cid):
		# return the name of a grading criteria associated with the id passed as an argument
		for criteria in self.rubric:
			try:
				if criteria['description'] == cid:
					return criteria['description']
				if criteria['description'] == cid:
					return criteria['description']
			except:
			 pass
		return None

		
		