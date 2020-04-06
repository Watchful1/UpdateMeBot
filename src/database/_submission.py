import discord_logging
from sqlalchemy.orm import joinedload

from classes.submission import Submission

log = discord_logging.get_logger()


class _DatabaseSubmission:
	def __init__(self):
		self.session = self.session  # for pycharm linting

	def get_submission_by_id(self, submission_id):
		log.debug(f"Fetching submission by id: {submission_id}")
		submission = self.session.query(Submission)\
			.options(joinedload(Submission.subreddit))\
			.filter_by(submission_id=submission_id)\
			.first()

		return submission

	def add_submission(self, submission):
		log.debug("Saving new submission")
		self.session.add(submission)
