import discord_logging

from classes.subscription import Subscription
from classes.user import User

log = discord_logging.get_logger()


class _DatabaseSubscriptions:
	def __init__(self):
		self.session = self.session  # for pycharm linting

	def add_subscription(self, subscription):
		log.debug("Saving new subscription")
		self.session.add(subscription)

	def get_subscription_by_fields(self, subscriber, author, subreddit):
		log.debug(f"Fetching subscription by fields: {subscriber.name} : {author.name} : {subreddit.name}")

		subscription = self.session.query(Subscription)\
			.filter(Subscription.subscriber == subscriber)\
			.filter(Subscription.author == author)\
			.filter(Subscription.subreddit == subreddit)\
			.first()

		return subscription

	def get_subscriptions_for_author_subreddit(self, author, subreddit):
		log.debug(f"Fetching subscriptions by author and subreddit: {author.name} : {subreddit.name}")

		subscriptions = self.session.query(Subscription)\
			.filter(Subscription.author == author)\
			.filter(Subscription.subreddit == subreddit)\
			.all()

		return subscriptions

	def get_user_subscriptions_by_name(self, user_name):
		user = self.session.query(User).filter_by(name=user_name).first()
		if user is None:
			return []
		else:
			return self.get_user_subscriptions(user)

	def get_user_subscriptions(self, user):
		log.debug(f"Fetching user subscriptions u/{user.name}")

		subscriptions = self.session.query(Subscription)\
			.filter(Subscription.subscriber == user)\
			.all()

		return sorted(subscriptions, key=lambda subscription: (subscription.subreddit.name, subscription.author.name))

	def delete_user_subscriptions(self, user):
		log.debug(f"Deleting all subscriptions for u/{user.name}")

		return self.session.query(Subscription)\
			.filter(Subscription.subscriber == user)\
			.delete(synchronize_session='fetch')

	def delete_subscription(self, subscription):
		log.debug(f"Deleting subscription by id: {subscription.id}")
		self.session.delete(subscription)
