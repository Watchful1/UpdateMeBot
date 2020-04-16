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

	def render_notification(self):
		bldr = utils.str_bldr()
		bldr.append("UpdateMeBot here!")
		bldr.append("\n\n")

		bldr.append("u/")
		bldr.append(self.subscription.author.name)
		bldr.append(" has posted a new thread in r/")
		bldr.append(self.subscription.subreddit.name)
		bldr.append("\n\n")

		bldr.append("You can find it here: ")
		bldr.append(self.submission.url)
		bldr.append("\n\n")

		bldr.append("*****")
		bldr.append("\n\n")

		if self.subscription.recurring:
			bldr.append("[Click here](")
			bldr.append(utils.build_message_link(
				static.ACCOUNT_NAME,
				"Remove",
				f"Remove u/{self.subscription.author.name} r/{self.subscription.subreddit.name}"
			))
			bldr.append(") to remove your subscription.")
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
