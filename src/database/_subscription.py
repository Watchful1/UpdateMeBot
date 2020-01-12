import discord_logging
from sqlalchemy.orm import joinedload

from classes.subscription import Subscription
from classes.user import User

log = discord_logging.get_logger()


class _DatabaseSubscriptions:
	def __init__(self):
		self.session = self.session  # for pycharm linting

	def add_subscription(self, subscription):
		log.debug("Saving new subscription")
		self.session.add(subscription)
