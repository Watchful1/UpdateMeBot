import utils
import discord_logging
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship

import static
from database import Base


log = discord_logging.get_logger()


class Subscription(Base):
	__tablename__ = 'subscriptions'
	__table_args__ = (UniqueConstraint('subscriber_id', 'subscribed_to_id', 'subreddit_id'),)

	id = Column(Integer, primary_key=True)
	subscriber_id = Column(Integer, ForeignKey('users.id'), nullable=False)
	subscribed_to_id = Column(Integer, ForeignKey('users.id'), nullable=False)
	subreddit_id = Column(Integer, ForeignKey('subreddits.id'), nullable=False)
	recurring = Column(Boolean, nullable=False)

	subscriber = relationship("User", foreign_keys=[subscriber_id])
	subscribed_to = relationship("User", foreign_keys=[subscribed_to_id])
	subreddit = relationship("Subreddit")

	def __init__(
		self,
		subscriber,
		subscribed_to,
		subreddit,
		recurring
	):
		self.subscriber = subscriber
		self.subscribed_to = subscribed_to
		self.subreddit = subreddit
		self.recurring = recurring
