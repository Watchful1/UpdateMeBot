import discord_logging
from sqlalchemy.orm import joinedload

from classes.message import Message

log = discord_logging.get_logger()


class _DatabaseMessage:
	def __init__(self):
		self.session = self.session  # for pycharm linting

	def add_message(self, message):
		log.debug("Saving new message")
		self.session.add(message)
