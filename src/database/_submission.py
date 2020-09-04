import discord_logging

from classes.submission import Submission

log = discord_logging.get_logger()


class _DatabaseSubmission:
	def __init__(self):
		self.session = self.session  # for pycharm linting
		self.log_debug = self.log_debug

	def get_submission_by_id(self, submission_id):
		if self.log_debug:
			log.debug(f"Fetching submission by id: {submission_id}")
		submission = self.session.query(Submission)\
			.filter_by(submission_id=submission_id)\
			.first()

		return submission

	def add_submission(self, submission):
		if self.log_debug:
			log.debug("Saving new submission")
		self.session.add(submission)

	def delete_submission(self, submission):
		if self.log_debug:
			log.debug(f"Deleting submission by id: {submission.id}")
		self.session.delete(submission)

	def get_old_orphan_submissions(self, before_date):
		if self.log_debug:
			log.debug(f"Getting orphaned submissions created before: {before_date}")

		results = self.session.query(Submission)\
			.filter(Submission.messages_sent == 0)\
			.filter(Submission.comment == None)\
			.filter(Submission.time_created < before_date)\
			.all()

		return results

	def get_count_submissions_for_author(self, user):
		if self.log_debug:
			log.debug(f"Getting count submissions for u/{user}")
		return self.session.query(Submission)\
			.filter(Submission.author == user)\
			.count()

	def delete_author_submissions(self, user):
		if self.log_debug:
			log.debug(f"Deleting all submissions by u/{user.name}")

		return self.session.query(Submission)\
			.filter(Submission.author == user)\
			.delete(synchronize_session='fetch')
