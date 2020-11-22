import discord_logging
from sqlalchemy.sql import func
from sqlalchemy import and_

from classes.comment import DbComment
from classes.submission import Submission
from classes.subscription import Subscription
from classes.subreddit import Subreddit
from classes.user import User

log = discord_logging.get_logger()


class _DatabaseComments:
	def __init__(self):
		self.session = self.session  # for pycharm linting

	def add_comment(self, db_comment):
		log.debug("Saving new comment")
		self.session.add(db_comment)

	def get_comment_by_thread(self, submission_id):
		log.debug(f"Fetching comment for thread: {submission_id}")

		return self.session.query(DbComment)\
			.join(Submission)\
			.filter(Submission.submission_id == submission_id)\
			.first()

	def delete_comment_by_thread(self, submission_id):
		log.debug(f"Deleting comment by thread id: {submission_id}")

		return self.session.query(DbComment)\
			.filter(DbComment.submission_id == submission_id)\
			.delete(synchronize_session='fetch')

	def delete_comment(self, db_comment):
		log.debug(f"Deleting comment by id: {db_comment.id}")
		self.session.delete(db_comment)

	def get_pending_incorrect_comments(self):
		log.debug("Fetching count of incorrect comments")

		subquery = self.session.query(Subscription.author_id, Subscription.subreddit_id, func.count('*').label("new_count"))\
			.group_by(Subscription.author_id, Subscription.subreddit_id)\
			.subquery()

		count = self.session.query(DbComment, subquery.c.new_count) \
			.join(DbComment.author) \
			.join(DbComment.subreddit) \
			.join(subquery, and_(User.id == subquery.c.author_id, Subreddit.id == subquery.c.subreddit_id)) \
			.filter(subquery.c.new_count != DbComment.current_count) \
			.count()
		log.debug(f"Incorrect comments: {count}")
		return count

	def get_incorrect_comments(self, count):
		log.debug(f"Fetching incorrect comments")

		subquery = self.session.query(Subscription.author_id, Subscription.subreddit_id, func.count('*').label("new_count"))\
			.group_by(Subscription.author_id, Subscription.subreddit_id)\
			.subquery()

		results = self.session.query(DbComment, subquery.c.new_count)\
			.join(DbComment.author)\
			.join(DbComment.subreddit)\
			.join(subquery, and_(User.id == subquery.c.author_id, Subreddit.id == subquery.c.subreddit_id))\
			.filter(subquery.c.new_count != DbComment.current_count)\
			.limit(count)\
			.all()

		log.debug(f"Found incorrect comments: {len(results)}")
		return results

	def get_old_comments(self, before_date):
		log.debug(f"Getting comments created before: {before_date}")

		results = self.session.query(DbComment)\
			.filter(DbComment.time_created < before_date)\
			.all()

		return results

	def delete_user_comments(self, user):
		log.debug(f"Deleting all comments for u/{user.name}")

		return self.session.query(DbComment)\
			.filter(DbComment.subscriber == user)\
			.delete(synchronize_session='fetch')

	def get_all_comments(self):
		return self.session.query(DbComment).all()

	def get_count_all_comments(self):
		return self.session.query(DbComment).count()
