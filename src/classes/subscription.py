import discord_logging
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship

from database import Base
import utils
import static


log = discord_logging.get_logger()


class Subscription(Base):
	__tablename__ = 'subscriptions'
	__table_args__ = (UniqueConstraint('subscriber_id', 'author_id', 'subreddit_id', 'tag'),)

	id = Column(Integer, primary_key=True)
	subscriber_id = Column(Integer, ForeignKey('users.id'), nullable=False)
	author_id = Column(Integer, ForeignKey('users.id'))
	subreddit_id = Column(Integer, ForeignKey('subreddits.id'), nullable=False)
	recurring = Column(Boolean, nullable=False)
	tag = Column(String(200, collation="NOCASE"))

	subscriber = relationship("User", foreign_keys=[subscriber_id], lazy="joined")
	author = relationship("User", foreign_keys=[author_id], lazy="joined")
	subreddit = relationship("Subreddit", lazy="joined")

	def __init__(
		self,
		subscriber,
		author,
		subreddit,
		recurring,
		tag=None
	):
		self.subscriber = subscriber
		self.author = author
		self.subreddit = subreddit
		self.recurring = recurring
		self.tag = tag

	@staticmethod
	def create_update_subscription(
		database,
		subscriber,
		author,
		subreddit,
		recurring,
		tag=None
	):
		if subreddit.is_blacklisted:
			log.info(
				f"Subreddit blacklisted r/{subreddit.name}, not adding subscription")
			result_message = \
				f"u/UpdateMeBot is not suited for subreddits like r/{subreddit.name}. It only works well in subs where" \
				f" the original poster of the thread will post a followup as a new thread. It's also possible this" \
				f" subreddit doesn't exist"
			return result_message, None
		if author is not None and author.name == "username":
			log.info(
				f"User blacklisted r/{author.name}, not adding subscription")
			result_message = \
				f"You have to set the username you want to reply to, it was left as u/username. Please try again"
			return result_message, None

		subscription = database.get_subscription_by_fields(subscriber, author, subreddit, tag)
		if subscription is not None:
			if subscription.recurring == recurring:
				if tag is not None:
					if author is None:
						log.info(
							f"u/{subscriber.name} already {'subscribed' if recurring else 'updated'} to <{tag}> in "
							f" r/{subreddit.name}")
						result_message = f"You had already asked me to message you for " \
							f"{'each' if recurring else 'next'} post tagged <{tag}> in r/{subreddit.name}"
					else:
						log.info(
							f"u/{subscriber.name} already {'subscribed' if recurring else 'updated'} to <{tag}> from "
							f"u/{author.name} in r/{subreddit.name}")
						result_message = f"You had already asked me to message you {'each' if recurring else 'next'} " \
							f"time u/{author.name} posts stories tagged <{tag}> in r/{subreddit.name}"
				else:
					if author is None:
						log.info(
							f"u/{subscriber.name} already {'subscribed' if recurring else 'updated'} to all posts in "
							f"r/{subreddit.name}")
						result_message = f"You had already asked me to message you {'each' if recurring else 'next'} " \
							f"post in r/{subreddit.name}"
					else:
						log.info(
							f"u/{subscriber.name} already {'subscribed' if recurring else 'updated'} to u/{author.name} in "
							f"r/{subreddit.name}")
						result_message = f"You had already asked me to message you {'each' if recurring else 'next'} time " \
							f"u/{author.name} posts in r/{subreddit.name}"

			else:
				if tag is not None:
					if author is None:
						log.info(
							f"u/{subscriber.name} changed from "
							f"{'update to subscription' if recurring else 'subscription to update'}"
							f" for <{tag}> in r/{subreddit.name}")
						result_message = f"I have updated your subscription type and will now message you " \
							f"{'each' if recurring else 'next'} post tagged <{tag}> in r/{subreddit.name}"
					else:
						log.info(
							f"u/{subscriber.name} changed from "
							f"{'update to subscription' if recurring else 'subscription to update'}"
							f" for <{tag}> from u/{author.name} in r/{subreddit.name}")
						result_message = f"I have updated your subscription type and will now message you " \
							f"{'each' if recurring else 'next'} time u/{author.name} posts stories tagged <{tag}> in " \
							f"r/{subreddit.name}"
				else:
					if author is None:
						log.info(
							f"u/{subscriber.name} changed from "
							f"{'update to subscription' if recurring else 'subscription to update'}"
							f" in r/{subreddit.name}")
						result_message = f"I have updated your subscription type and will now message you " \
							f"{'each' if recurring else 'next'} post in r/{subreddit.name}"
					else:
						log.info(
							f"u/{subscriber.name} changed from "
							f"{'update to subscription' if recurring else 'subscription to update'}"
							f" for u/{author.name} in r/{subreddit.name}")
						result_message = f"I have updated your subscription type and will now message you " \
							f"{'each' if recurring else 'next'} time u/{author.name} posts in r/{subreddit.name}"
				subscription.recurring = recurring

		else:
			if not subreddit.is_enabled:
				if author is None:
					log.info(f"Subscription added, -all, r/{subreddit.name}, {recurring}, subreddit not enabled")
				else:
					log.info(f"Subscription added, u/{author.name}, r/{subreddit.name}, {recurring}, subreddit not enabled")
				result_message = f"Subreddit r/{subreddit.name} is not being tracked by the bot. It will be automatically" \
					f" added if enough users request it. More details [here]({static.TRACKING_INFO_URL})"
				utils.check_update_disabled_subreddit(database, subreddit)

			elif subreddit.tag_enabled and tag is not None:
				subscription_all = database.get_subscription_by_fields(subscriber, author, subreddit)
				if subscription_all is not None:
					if author is None:
						log.info(
							f"u/{subscriber.name} already {'subscribed' if recurring else 'updated'} to all "
							f"in r/{subreddit.name}, not adding tag <{tag}>")
						result_message = f"You're already {'subscribed' if recurring else 'updated'} to all " \
							f"posts in r/{subreddit.name}. If you want to only get messages for " \
							f"<{tag}>, then you'll need to unsubscribe first"
					else:
						log.info(
							f"u/{subscriber.name} already {'subscribed' if recurring else 'updated'} to all "
							f"u/{author.name} in r/{subreddit.name}, not adding tag <{tag}>")
						result_message = f"You're already {'subscribed' if recurring else 'updated'} to all " \
							f"posts from u/{author.name} in r/{subreddit.name}. If you want to only get messages for " \
							f"<{tag}>, then you'll need to unsubscribe first"
					return result_message, None

				else:
					if author is None:
						log.info(f"Subscription added, -all, r/{subreddit.name}, {recurring}, {tag}")
						result_message = f"I will message you {'each' if recurring else 'next'} " \
							f"post tagged <{tag}> in r/{subreddit.name}"
					else:
						log.info(f"Subscription added, u/{author.name}, r/{subreddit.name}, {recurring}, {tag}")
						result_message = f"I will message you {'each' if recurring else 'next'} time u/{author.name} " \
							f"posts stories tagged <{tag}> in r/{subreddit.name}"

			elif subreddit.tag_enabled and database.get_count_tagged_subscriptions_by_fields(subscriber, author, subreddit):
				if author is None:
					log.info(
						f"u/{subscriber.name} has tagged subscriptions to in r/{subreddit.name} when "
						f"adding all, deleting")
					result_message = f"I will message you {'each' if recurring else 'next'} post in r/{subreddit.name}. " \
						f"This replaces your {'subscriptions' if recurring else 'updates'} to specific tagged posts there"
				else:
					log.info(
						f"u/{subscriber.name} has tagged subscriptions to u/{author.name} in r/{subreddit.name} when "
						f"adding all, deleting")
					result_message = f"I will message you {'each' if recurring else 'next'} time u/{author.name} " \
						f"posts in r/{subreddit.name}. This replaces your " \
						f"{'subscriptions' if recurring else 'updates'} to specific tagged posts of theirs"
				database.delete_tagged_subreddit_author_subscriptions(subscriber, author, subreddit)

			else:
				if author is None:
					log.info(f"Subscription added, -all, r/{subreddit.name}, {recurring}")
					result_message = f"I will message you {'each' if recurring else 'next'} " \
						f"post in r/{subreddit.name}"
				else:
					log.info(f"Subscription added, u/{author.name}, r/{subreddit.name}, {recurring}")
					result_message = f"I will message you {'each' if recurring else 'next'} time u/{author.name} " \
						f"posts in r/{subreddit.name}"

			subscription = Subscription(
				subscriber=subscriber,
				author=author,
				subreddit=subreddit,
				recurring=recurring,
				tag=tag
			)
			database.add_subscription(subscription)
			database.commit()

		return result_message, subscription

	def __str__(self):
		if self.author is None:
			return f"u/{self.subscriber.name} to r/{self.subreddit.name} : {self.recurring}"
		else:
			return f"u/{self.subscriber.name} to u/{self.author.name} in r/{self.subreddit.name} : {self.recurring}"
