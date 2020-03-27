import discord_logging

from classes.user import User

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
