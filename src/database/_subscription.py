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

	def get_subscription_by_fields(self, subscriber_id, subscribed_to_id, subreddit_id):
		log.debug(f"Fetching subscription by fields: {subscriber_id} : {subscribed_to_id} : {subreddit_id}")

		subscription = self.session.query(Subscription)\
			.options(joinedload(Subscription.subscriber))\
			.options(joinedload(Subscription.subscribed_to))\
			.options(joinedload(Subscription.subreddit))\
			.filter_by(subscriber_id=subscriber_id)\
			.filter_by(subscribed_to_id=subscribed_to_id)\
			.filter_by(subreddit_id=subreddit_id)\
			.first()

		return subscription
