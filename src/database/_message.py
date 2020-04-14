import discord_logging
from sqlalchemy.orm import joinedload

from classes.message import Message
from classes.subscription import Subscription

log = discord_logging.get_logger()


class _DatabaseMessage:
	def __init__(self):
		self.session = self.session  # for pycharm linting

	def add_message(self, message):
		log.debug("Saving new message")
		self.session.add(message)

	def get_count_pending_messages(self):
		log.debug(f"Fetching count of pending messages")

		count = self.session.query(Message)\
			.order_by(Message.id)\
			.count()

		return count

	def get_pending_messages(self, count=9999):
		log.debug(f"Fetching pending messages")

		messages = self.session.query(Message)\
			.options(
				joinedload(Message.subscription)
				.joinedload(Message.submission)
				.joinedload(Subscription.subscriber)
				.joinedload(Subscription.subreddit)
				.joinedload(Subscription.author))\
			.order_by(Message.id)\
			.limit(count)\
			.all()

		return messages

	def clear_all_messages(self):
		log.debug(f"Clearing all messages in queue")

		self.session.query(Message)\
			.delete(synchronize_session='fetch')
