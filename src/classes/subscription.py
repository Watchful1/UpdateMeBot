import discord_logging
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship

from database import Base


log = discord_logging.get_logger()


class Subscription(Base):
	__tablename__ = 'subscriptions'
	__table_args__ = (UniqueConstraint('subscriber_id', 'author_id', 'subreddit_id'),)

	id = Column(Integer, primary_key=True)
	subscriber_id = Column(Integer, ForeignKey('users.id'), nullable=False)
	author_id = Column(Integer, ForeignKey('users.id'), nullable=False)
	subreddit_id = Column(Integer, ForeignKey('subreddits.id'), nullable=False)
	recurring = Column(Boolean, nullable=False)

	subscriber = relationship("User", foreign_keys=[subscriber_id], lazy="joined")
	author = relationship("User", foreign_keys=[author_id], lazy="joined")
	subreddit = relationship("Subreddit", lazy="joined")

	def __init__(
		self,
		subscriber,
		author,
		subreddit,
		recurring
	):
		self.subscriber = subscriber
		self.author = author
		self.subreddit = subreddit
		self.recurring = recurring
