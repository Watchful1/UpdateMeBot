from sqlalchemy import Column, Integer, String,  DateTime, ForeignKey
from database import Base
from sqlalchemy.orm import relationship

import utils
import static


class Notification(Base):
	__tablename__ = 'notifications'

	id = Column(Integer, primary_key=True)
	subscription_id = Column(Integer, ForeignKey('subscriptions.id'), nullable=False)
	submission_id = Column(Integer, ForeignKey('submissions.id'), nullable=False)

	subscription = relationship("Subscription", foreign_keys=[subscription_id], lazy="joined")
	submission = relationship("Submission", foreign_keys=[submission_id], lazy="joined")

	def __init__(
		self,
		subscription,
		submission
	):
		self.subscription = subscription
		self.submission = submission

	def __str__(self):
		return \
			f"u/{self.subscription.subscriber.name} to u/{self.subscription.author.name} in " \
			f"r/{self.subscription.subreddit.name} : u/{self.submission.id}"

	def render_notification(self):
		bldr = utils.str_bldr()
		bldr.append("UpdateMeBot here!")
		bldr.append("\n\n")

		if self.subscription.author == self.subscription.subscriber:
			bldr.append("I have finished sending out ")
			bldr.append(str(self.submission.messages_sent))
			bldr.append(" notifications for [your post](")
			bldr.append(self.submission.url)
			bldr.append(")")
			if self.submission.tag is not None:
				bldr.append(" with tag <")
				bldr.append(self.submission.tag)
				bldr.append(">")
			bldr.append(".")
			bldr.append("\n\n")

		else:
			bldr.append("u/")
			bldr.append(self.subscription.author.name)
			bldr.append(" has posted a new thread")
			if self.submission.tag is not None:
				bldr.append(" with the tag <")
				bldr.append(self.submission.tag)
				bldr.append(">")
			bldr.append(" in r/")
			bldr.append(self.subscription.subreddit.name)
			bldr.append("\n\n")

			bldr.append("You can find it here: ")
			bldr.append(self.submission.url)
			bldr.append("\n\n")

		bldr.append("*****")
		bldr.append("\n\n")

		if self.subscription.recurring:
			bldr.append("[Click here](")
			if self.subscription.tag is not None:
				bldr.append(utils.build_message_link(
					static.ACCOUNT_NAME,
					"Remove",
					f"Remove u/{self.subscription.author.name} r/{self.subscription.subreddit.name}"
					f"{' <'+self.submission.tag+'>'}"
				))
				bldr.append(") to remove your subscription for the tag <")
				bldr.append(self.submission.tag)
				bldr.append(">.  \nOr ")
				bldr.append("[Click here](")

			bldr.append(utils.build_message_link(
				static.ACCOUNT_NAME,
				"Remove",
				f"Remove u/{self.subscription.author.name} r/{self.subscription.subreddit.name}"
			))
			bldr.append(") to remove your subscription")

			if self.subscription.tag is not None:
				bldr.append(" to all tagged stories")

			bldr.append(".")
		else:
			if self.subscription.tag is not None:
				bldr.append("[Click here](")
				bldr.append(utils.build_message_link(
					static.ACCOUNT_NAME,
					"Update",
					f"UpdateMe u/{self.subscription.author.name} r/{self.subscription.subreddit.name}"
					f"{' <'+self.submission.tag+'>'}"
				))
				bldr.append(") if you want to be messaged the next time too  \n")

				bldr.append("Or [Click here](")
				bldr.append(utils.build_message_link(
					static.ACCOUNT_NAME,
					"Subscribe",
					f"SubscribeMe u/{self.subscription.author.name} r/{self.subscription.subreddit.name}"
					f"{' <'+self.submission.tag+'>'}"
				))
				bldr.append(") if you want to be messaged every time")
			else:
				bldr.append("[Click here](")
				bldr.append(utils.build_message_link(
					static.ACCOUNT_NAME,
					"Update",
					f"UpdateMe u/{self.subscription.author.name} r/{self.subscription.subreddit.name}"
				))
				bldr.append(") if you want to be messaged the next time too  \n")

				bldr.append("Or [Click here](")
				bldr.append(utils.build_message_link(
					static.ACCOUNT_NAME,
					"Subscribe",
					f"SubscribeMe u/{self.subscription.author.name} r/{self.subscription.subreddit.name}"
				))
				bldr.append(") if you want to be messaged every time")

		return bldr
