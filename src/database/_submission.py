import discord_logging
from sqlalchemy.sql import func, or_
from datetime import timedelta

from classes.submission import Submission
from classes.notification import Notification
import utils

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

	def get_submissions_with_notifications(self, notification_limit=30):
		subquery = self.session.query(Notification.submission_id, func.count('*').label("count"))\
			.group_by(Notification.submission_id)\
			.subquery()

		results = self.session.query(Submission)\
			.join(subquery, Submission.id == subquery.c.submission_id)\
			.filter(subquery.c.count >= notification_limit) \
			.all()

		return results

	def get_count_submissions_for_rescan(self, created_date):
		return self.session.query(Submission)\
			.filter(Submission.messages_sent > 0)\
			.filter(Submission.rescanned == False)\
			.filter(Submission.time_created < created_date)\
			.count()

	def get_submissions_for_rescan(self, created_date, count):
		return self.session.query(Submission)\
			.filter(Submission.messages_sent > 0)\
			.filter(Submission.rescanned == False)\
			.filter(Submission.time_created < created_date)\
			.limit(count)\
			.all()

	def get_count_submissions_for_author(self, user):
		if self.log_debug:
			log.debug(f"Getting count submissions for u/{user}")
		return self.session.query(Submission)\
			.filter(Submission.author == user)\
			.count()

	def get_recent_submissions_for_author(self, user, subreddit, current_submission_id, count_submissions):
		if self.log_debug:
			log.debug(f"Getting count submissions for u/{user}")

		return self.session.query(Submission)\
			.filter(Submission.author == user) \
			.filter(Submission.subreddit == subreddit) \
			.filter(Submission.id != current_submission_id) \
			.order_by(Submission.time_created.desc())\
			.limit(count_submissions)\
			.all()

	def delete_author_submissions(self, user):
		if self.log_debug:
			log.debug(f"Deleting all submissions by u/{user.name}")

		return self.session.query(Submission)\
			.filter(Submission.author == user)\
			.delete(synchronize_session='fetch')

	def get_count_all_submissions(self):
		if self.log_debug:
			log.debug(f"Getting count all submissions")
		return self.session.query(Submission)\
			.count()

	def get_all_submissions(self):
		if self.log_debug:
			log.debug(f"Getting all submissions")

		return self.session.query(Submission)\
			.all()
