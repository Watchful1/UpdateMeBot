from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from database import Base

import utils
import static


class DbComment(Base):
	__tablename__ = 'comments'

	id = Column(Integer, primary_key=True)
	comment_id = Column(String(12), nullable=False, unique=True)
	submission_id = Column(String(12), ForeignKey('submissions.id'), nullable=False)
	subscriber_id = Column(Integer, ForeignKey('users.id'), nullable=False)
	author_id = Column(Integer, ForeignKey('users.id'), nullable=False)
	subreddit_id = Column(Integer, ForeignKey('subreddits.id'), nullable=False)
	recurring = Column(Boolean, nullable=False)
	current_count = Column(Integer, nullable=False)
	tag = Column(String(200, collation="NOCASE"))
	time_created = Column(DateTime(), nullable=False)

	submission = relationship("Submission", lazy="joined")
	subscriber = relationship("User", foreign_keys=[subscriber_id], lazy="joined")
	author = relationship("User", foreign_keys=[author_id], lazy="joined")
	subreddit = relationship("Subreddit", lazy="joined")

	def __init__(
		self,
		comment_id,
		submission,
		subscriber,
		author,
		subreddit,
		recurring,
		current_count=1,
		tag=None
	):
		self.comment_id = comment_id
		self.submission = submission
		self.subscriber = subscriber
		self.author = author
		self.subreddit = subreddit
		self.recurring = recurring
		self.current_count = current_count
		self.tag = tag
		self.time_created = utils.datetime_now()

	def __str__(self):
		return f"{self.comment_id} : u/{self.subscriber.name}"

	def render_comment(self, count_subscriptions=1, comment_age_seconds=0):
		bldr = utils.str_bldr()
		if comment_age_seconds > (60 * 60):
			bldr.append("I'm really sorry about replying to this so late. There's a [detailed post about why I did here](")
			bldr.append("https://www.reddit.com/r/UpdateMeBot/comments/13isv2q/updatemebot_is_now_replying_to_comments_again/")
			bldr.append(").")
			bldr.append("\n\n")

		bldr.append("I will message you ")
		if self.recurring:
			bldr.append("each")
		else:
			bldr.append("next")
		bldr.append(" time u/")
		bldr.append(self.author.name)
		bldr.append(" posts")
		if self.tag is not None:
			bldr.append(" a story tagged <")
			bldr.append(self.tag)
			bldr.append(">")
		bldr.append(" in r/")
		bldr.append(self.subreddit.name)
		bldr.append(".")

		bldr.append("\n\n")

		bldr.append("[Click this link](")
		bldr.append(utils.build_message_link(
			static.ACCOUNT_NAME,
			"Update",
			f"{static.TRIGGER_SUBSCRIBE if self.recurring else static.TRIGGER_UPDATE}! u/{self.author.name} "
			f"r/{self.subreddit.name}"
		))
		bldr.append(") to ")
		if count_subscriptions > 1:
			bldr.append("join ")
			bldr.append(str(count_subscriptions))
			bldr.append(" others and")
		else:
			bldr.append("also")
		bldr.append(" be messaged. ")

		bldr.append("The parent author can [delete this post](")
		bldr.append(utils.build_message_link(
			static.ACCOUNT_NAME,
			"Delete",
			f"delete {self.submission.submission_id}"
		))
		bldr.append(")")

		return bldr
