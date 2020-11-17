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
			f"u/{self.subscription.subscriber.name} to u/{self.submission.author.name} in " \
			f"r/{self.subscription.subreddit.name} : u/{self.submission.id}"

	def render_subject(self):
		bldr = utils.str_bldr()
		bldr.append("UpdateMeBot Here! Post by u/")
		bldr.append(self.submission.author.name)
		bldr.append(" in r/")
		bldr.append(self.submission.subreddit.name)

		if self.submission.title is not None:
			bldr.append(": ")

			characters_available = 100 - utils.bldr_length(bldr)
			if len(self.submission.title) > characters_available:
				bldr.append(self.submission.title[:characters_available-3])
				bldr.append("...")
			else:
				bldr.append(self.submission.title)

		return bldr

	def render_notification(self, recent_submissions=None):
		bldr = utils.str_bldr()
		target_is_author = self.subscription.author is not None and self.subscription.author == self.subscription.subscriber
		if not target_is_author and self.subscription.subscriber.short_notifs:
			bldr.append("New thread from u/")
			bldr.append(self.submission.author.name)
			if self.submission.tag is not None:
				bldr.append(" with the tag <")
				bldr.append(self.submission.tag)
				bldr.append(">")
			bldr.append(" in r/")
			bldr.append(self.subscription.subreddit.name)
			bldr.append(": ")

			if self.submission.title is not None:
				bldr.append("[**")
				bldr.append(self.submission.title)
				bldr.append("**](")
				bldr.append(self.submission.url)
				bldr.append(")")
			else:
				bldr.append(self.submission.url)
			bldr.append("\n\n")

		else:
			bldr.append("UpdateMeBot here!")
			bldr.append("\n\n")

			if target_is_author:
				bldr.append("I have finished sending out ")
				if self.submission.messages_sent >= static.STAT_MINIMUM:
					bldr.append(str(self.submission.messages_sent))
					bldr.append(" ")
				bldr.append("notifications for [your post](")
				bldr.append(self.submission.url)
				bldr.append(")")
				if self.submission.tag is not None:
					bldr.append(" with tag <")
					bldr.append(self.submission.tag)
					bldr.append(">")
				bldr.append(".")

			else:
				bldr.append("u/")
				bldr.append(self.submission.author.name)
				bldr.append(" has posted a new thread")
				if self.submission.tag is not None:
					bldr.append(" with the tag <")
					bldr.append(self.submission.tag)
					bldr.append(">")
				bldr.append(" in r/")
				bldr.append(self.subscription.subreddit.name)
				bldr.append("\n\n")

				if self.submission.title is not None:
					bldr.append("[**")
					bldr.append(self.submission.title)
					bldr.append("**](")
					bldr.append(self.submission.url)
					bldr.append(")")
				else:
					bldr.append("You can find it here: ")
					bldr.append(self.submission.url)

			bldr.append("\n\n")

			if recent_submissions is not None and len(recent_submissions):
				bldr.append("*****")
				bldr.append("\n\n")

				bldr.append("Recent posts:[*](")
				bldr.append(static.ABBREV_POST)
				bldr.append(")  \n")
				for submission in recent_submissions:
					if submission.title is not None:
						bldr.append("[")
						bldr.append(submission.title)
						bldr.append("](")
						bldr.append(submission.url)
						bldr.append(")  \n")
					else:
						bldr.append(submission.url)
						bldr.append("  \n")
				bldr.append("\n")

			bldr.append("*****")
			bldr.append("\n\n")

		if self.subscription.recurring:
			if self.subscription.tag is not None:
				bldr.append("[Click here](")
				if self.subscription.author is None:
					message_text = f"Remove r/{self.subscription.subreddit.name} -all {' <'+self.submission.tag+'>'}"
				else:
					message_text = \
						f"Remove u/{self.submission.author.name} r/{self.subscription.subreddit.name}" \
						f"{' <'+self.submission.tag+'>'}"
				bldr.append(utils.build_message_link(static.ACCOUNT_NAME, "Remove", message_text))
				bldr.append(") to remove your subscription for the tag <")
				bldr.append(self.submission.tag)
				bldr.append(">.  \nOr ")

			bldr.append("[Click here](")

			if self.subscription.author is None:
				message_text = f"Remove r/{self.subscription.subreddit.name} -all"
			else:
				message_text = f"Remove u/{self.submission.author.name} r/{self.subscription.subreddit.name}"
			bldr.append(utils.build_message_link(static.ACCOUNT_NAME, "Remove", message_text))
			bldr.append(") to remove your subscription")

			if self.subscription.tag is not None:
				bldr.append(" to all tagged stories")

			bldr.append(".")
		else:
			if self.subscription.tag is not None:
				if self.subscription.author is None:
					message_text = f"{{}} r/{self.subscription.subreddit.name} -all {' <'+self.submission.tag+'>'}"
				else:
					message_text = \
						f"{{}} u/{self.submission.author.name} r/{self.subscription.subreddit.name}" \
						f"{' <'+self.submission.tag+'>'}"
			else:
				if self.subscription.author is None:
					message_text = f"{{}} r/{self.subscription.subreddit.name} -all"
				else:
					message_text = f"{{}} u/{self.submission.author.name} r/{self.subscription.subreddit.name}"
			bldr.append("[Click here](")
			bldr.append(utils.build_message_link(static.ACCOUNT_NAME, "Update", message_text.format("UpdateMe")))
			bldr.append(") if you want to be messaged the next time too  \n")

			bldr.append("Or [Click here](")
			bldr.append(utils.build_message_link(static.ACCOUNT_NAME, "Subscribe", message_text.format("SubscribeMe")))
			bldr.append(") if you want to be messaged every time")

		return bldr
