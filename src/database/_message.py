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

	def get_all_pending_messages(self):
		log.debug(f"Fetching all messages")

		messages = self.session.query(Message)\
			.options(joinedload(Message.subscription))\
			.options(joinedload(Message.submission))\
			.order_by(Message.id)\
			.all()

		return messages

	def clear_all_messages(self):
		log.debug(f"Clearing all messages in queue")

		self.session.query(Message)\
			.delete(synchronize_session='fetch')
