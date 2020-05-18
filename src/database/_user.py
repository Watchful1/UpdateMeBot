import discord_logging
from sqlalchemy.orm import aliased

from classes.user import User
from classes.submission import Submission
from classes.subscription import Subscription
from classes.comment import DbComment
from classes.stat import Stat

log = discord_logging.get_logger()


class _DatabaseUsers:
	def __init__(self):
		self.session = self.session  # for pycharm linting

	def get_or_add_user(self, user_name, case_is_user_supplied=False):
		log.debug(f"Fetching user: {user_name}")
		user = self.session.query(User).filter_by(name=user_name).first()
		if user is None:
			log.debug(f"Creating user: {user_name}")
			user = User(user_name)
			self.session.add(user)
		else:
			if user.name != user_name and not case_is_user_supplied and user_name != user_name.lower():
				user.name = user_name

		return user

	def get_user(self, user_name):
		log.debug(f"Fetching user: {user_name}")
		user = self.session.query(User).filter_by(name=user_name).first()

		return user

	def delete_user(self, user):
		log.debug(f"Deleting user by id: {user.id}")
		self.session.delete(user)

	def get_orphan_users(self):
		log.debug(f"Getting orphaned users")

		DbComment1 = aliased(DbComment)
		DbComment2 = aliased(DbComment)
		Subscription1 = aliased(Subscription)
		Subscription2 = aliased(Subscription)
		users = self.session.query(User) \
			.outerjoin(Submission, Submission.author_id == User.id) \
			.outerjoin(DbComment1, DbComment1.author_id == User.id) \
			.outerjoin(DbComment2, DbComment2.subscriber_id == User.id) \
			.outerjoin(Subscription1, Subscription1.author_id == User.id) \
			.outerjoin(Subscription2, Subscription2.subscriber_id == User.id) \
			.outerjoin(Stat, Stat.author_id == User.id) \
			.filter(Submission.id == None) \
			.filter(DbComment1.id == None) \
			.filter(DbComment2.id == None) \
			.filter(Subscription1.id == None) \
			.filter(Subscription2.id == None) \
			.filter(Stat.id == None) \
			.all()

		return users
