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

	def get_subscription_by_fields(self, subscriber, subscribed_to, subreddit):
		log.debug(f"Fetching subscription by fields: {subscriber.name} : {subscribed_to.name} : {subreddit.name}")

		subscription = self.session.query(Subscription)\
			.options(joinedload(Subscription.subscriber))\
			.options(joinedload(Subscription.subscribed_to))\
			.options(joinedload(Subscription.subreddit))\
			.filter(Subscription.subscriber == subscriber)\
			.filter(Subscription.subscribed_to == subscribed_to)\
			.filter(Subscription.subreddit == subreddit)\
			.first()

		return subscription

	def get_user_subscriptions(self, user):
		log.debug(f"Fetching user subscriptions u/{user.name}")

		subscriptions = self.session.query(Subscription)\
			.options(joinedload(Subscription.subscriber))\
			.options(joinedload(Subscription.subscribed_to))\
			.options(joinedload(Subscription.subreddit))\
			.filter(Subscription.subscriber == user)\
			.order_by(Subscription.subreddit.name)\
			.order_by(Subscription.subscribed_to.name)\
			.all()

		return subscriptions

	def delete_user_subscriptions(self, user):
		log.debug(f"Deleting all subscriptions for u/{user.name}")

		return self.session.query(Subscription)\
			.filter(Subscription.subscriber == user)\
			.delete(synchronize_session='fetch')

	def delete_subscription(self, subscription):
		log.debug(f"Deleting subscription by id: {subscription.id}")
		self.session.delete(subscription)
