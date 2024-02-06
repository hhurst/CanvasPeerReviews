class Review:
	# a 'Review' object represents a completed peer review (called an 'assessment'
	# by the canvasapi.  It includes (among other things) the creation being reviewed, information about
	# which assignment it was submitted to, who the reviewer was, and who the author
	# of the creation was.  
	def __init__(self, assessment, creation, rubric_outcomes, thisAssignment=None):
		self.creation=creation
		self.assessment=assessment
		self.review_type=assessment['assessment_type']
		self.reviewer_id = assessment['assessor_id']
		self.author_id = creation.user_id
		self.assignment_id = creation.assignment_id
		self.submission_id = assessment['artifact_id']
		self.id=assessment['id']
		self.excused = False		
		self.data = assessment['data']
		for outcome in range(len(self.data)):
			self.data[outcome]['cid']=None
			self.data[outcome]['cid']=None
			for rubric_outcome in rubric_outcomes:
				if self.data[outcome]['criterion_id'] == rubric_outcome['id']:
					self.data[outcome]['cid']=rubric_outcome['description']
			#self.data[outcome]['cid']=graded_assignments[creation.assignment_id].rubric[outcome]['description']
		self.scores=dict()
		self.comments=dict()
		self.minimumRequiredCommentLength=2
		self.urls=[]
		
		self.descriptionFromId=dict()
		for criteria in thisAssignment.rubric:
			self.descriptionFromId[criteria['id']]=criteria['description']
		
		try:
			for attachment in self.creation.attachments:
				previewURL=attachment['url'].split("/download")[0]
				self.urls.append(attachment['url'])
				#self.urls.append(previewURL)
		except:
			previewURL=None
			self.urls.append(None)
		self.url=self.urls[0]
		for s in self.data:
			try:
				#self.scores[s['criterion_id']]=s['points']
				#self.comments[s['criterion_id']]=s['comments']
				#self.scores[s['cid']]=s['points']
				#self.comments[s['cid']]=s['comments']
				self.scores[self.descriptionFromId[s['description']]]=s['points']
				self.comments[self.descriptionFromId[s['description']]]=s['comments']
			except:
				err="Unscored criteria"

	def getComments(self): # this takes a bit of time so we have it as a separate function outside the init block so that we don't have to spend the time if we don't need it.
		# this returns all comments that the reviewer made on the creation, whether they
		# are embedded in the rubric form, or added as a general comment.  It will 
		# also check to see if the length of the aggregated comments exceed some 
		# threshold parameter (minimumRequiredCommentLength) and set a 'commented'
		# parameter with the result.  This is useful if you wish to require that
		# reviewers leave comments.
		for s in self.data:
			try:
				#self.comments[s['criterion_id']]=s['comments']
				self.comments[self.descriptionFromId[s['description']]]=s['comments']
			except:
				err="Unscored criteria"
		ce=self.creation.edit()
		if (self.review_type == "grading"):
			commentToIgnore=self.creation.author.comments[self.assignment_id]
			self.commentToIgnore=commentToIgnore
			self.ce=ce
			theComments=[comment_item['comment'] for comment_item in ce.submission_comments if comment_item['author_id']==self.reviewer_id]
			theCommentsToInclude=[c for c in theComments if c!=commentToIgnore]
			self.comments[0]="\n\n".join(theCommentsToInclude)
		else:
			self.comments[0]="\n\n".join([comment_item['comment'] for comment_item in ce.submission_comments if comment_item['author_id']==self.reviewer_id])
		self.allComments="\n".join(self.comments.values()).strip()
		self.commented=len(self.allComments)>self.minimumRequiredCommentLength 
		return self.allComments
					
				
	def disp(self):
		msg = "(" + str(self.reviewer_id) + ") review of submission by (" + str(self.author_id) + "): "
		msg += "["
		for s in self.data:
			try:
				#msg+="Criteria" +str(s['criterion_id']) + " " + str(s['points'])+", "
				msg+="Criteria" + self.descriptionFromId[s['description']] + " " + str(s['points'])+", "
			except:
				#msg+="Criteria" +str(s['criterion_id']) + " " + "---, "
				msg+="Criteria" +self.descriptionFromId[s['description']] + " " + "---, "
		msg=msg[0:-2]+ "]"			
		return msg
		
	def fingerprint(self):
		#this is a unique string identifying the review in a more meaningful way than the id
		return "assignment_id=" + str(self.assignment_id) + "&author_id=" + str(self.author_id) + "&reviewer_id="+str(self.reviewer_id)