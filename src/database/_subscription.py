import discord_logging
from sqlalchemy.sql import func

import utils
from classes.subscription import Subscription
from classes.subreddit import Subreddit
from classes.user import User
from classes.notification import Notification

log = discord_logging.get_logger()


class _DatabaseSubscriptions:
	def __init__(self):
		self.session = self.session  # for pycharm linting

	def add_subscription(self, subscription):
		log.debug("Saving new subscription")
		self.session.add(subscription)

	def get_subscription_by_fields(self, subscriber, author, subreddit, tag=None):
		log.debug(
			f"Fetching subscription by fields: {subscriber.name} : {author.name if author is not None else '-all'} "
			f": {subreddit.name}: {tag}")

		subscription = self.session.query(Subscription)\
			.filter(Subscription.subscriber == subscriber)\
			.filter(Subscription.author == author)\
			.filter(Subscription.subreddit == subreddit)\
			.filter(Subscription.tag == tag)\
			.first()

		return subscription

	def get_count_tagged_subscriptions_by_fields(self, subscriber, author, subreddit):
		log.debug(f"Fetching count of tagged subscription by fields: {subscriber.name} : {author.name} : {subreddit.name}")

		count_subscriptions = self.session.query(Subscription)\
			.filter(Subscription.subscriber == subscriber)\
			.filter(Subscription.author == author)\
			.filter(Subscription.subreddit == subreddit)\
			.filter(Subscription.tag != None)\
			.count()

		return count_subscriptions

	def get_count_subscriptions_for_author_subreddit(self, author, subreddit, tag=None):
		log.debug(f"Fetching count subscriptions for author and subreddit: {author.name} : {subreddit.name}: {tag}")

		count_subscriptions = self.session.query(Subscription)\
			.filter(Subscription.author == author)\
			.filter(Subscription.subreddit == subreddit)\
			.filter(Subscription.tag == tag)\
			.count()

		return count_subscriptions

	def get_count_subscriptions_for_subreddit(self, subreddit):
		log.debug(f"Fetching count subscriptions for subreddit: {subreddit.name}")

		count_subscriptions = self.session.query(Subscription)\
			.filter(Subscription.subreddit == subreddit)\
			.count()

		return count_subscriptions

	def get_subscriptions_for_author_subreddit(self, author, subreddit, tag=None):
		log.debug(f"Fetching subscriptions by author and subreddit: {author.name} : {subreddit.name} : {tag}")

		subscriptions = self.session.query(Subscription)\
			.join(
				Notification,
				(Subscription.recurring == False) & (Notification.subscription_id == Subscription.id),
				isouter=True) \
			.filter((Subscription.author == author) | (Subscription.author == None))\
			.filter(Subscription.subreddit == subreddit)\
			.filter((Subscription.tag == None) | (Subscription.tag == tag))\
			.filter(Notification.id == None) \
			.all()

		return sorted(
			subscriptions,
			key=lambda subscription: (
				subscription.subscriber.name == (subscription.author.name if subscription.author is not None else ""),
				subscription.subscriber.id
			)
		)

	def get_user_subscriptions_by_name(self, user_name, only_enabled=True):
		user = self.session.query(User).filter_by(name=user_name).first()
		if user is None:
			return []
		else:
			return self.get_user_subscriptions(user, only_enabled)

	def get_user_subscriptions(self, user, only_enabled=True):
		log.debug(f"Fetching user subscriptions u/{user.name}")

		if only_enabled:
			subscriptions = self.session.query(Subscription)\
				.join(Subreddit)\
				.filter(Subreddit.is_enabled == True)\
				.filter(Subscription.subscriber == user)\
				.all()
		else:
			subscriptions = self.session.query(Subscription)\
				.filter(Subscription.subscriber == user)\
				.all()

		return sorted(
			subscriptions,
			key=lambda subscription: (
				subscription.subreddit.name,
				subscription.author.name if subscription.author is not None else None,
				subscription.tag
			)
		)

	def get_count_subscriptions_for_author(self, user):
		log.debug(f"Getting count subscriptions for u/{user}")
		return self.session.query(Subscription)\
			.filter(Subscription.author == user)\
			.count()

	def delete_user_subscriptions(self, user):
		log.debug(f"Deleting all subscriptions for u/{user.name}")

		return self.session.query(Subscription)\
			.filter(Subscription.subscriber == user)\
			.delete(synchronize_session='fetch')

	def delete_tagged_subreddit_author_subscriptions(self, subscriber, author, subreddit):
		log.debug(f"Deleting all tagged subscriptions for u/{subscriber.name} : {subscriber.name} : {author.name} : {subreddit.name}")

		return self.session.query(Subscription)\
			.filter(Subscription.subscriber == subscriber)\
			.filter(Subscription.author == author)\
			.filter(Subscription.subreddit == subreddit)\
			.filter(Subscription.tag != None)\
			.delete(synchronize_session='fetch')

	def delete_subscription(self, subscription):
		log.debug(f"Deleting subscription by id: {subscription.id}")
		self.session.delete(subscription)

	def get_all_subscriptions(self):
		log.debug("Fetching all author subreddit subscriptions")
		subscriptions = self.session.query(Subscription)\
			.all()

		return subscriptions
