import discord_logging
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, UniqueConstraint
from sqlalchemy.orm import relationship

from database import Base


log = discord_logging.get_logger()


class Stat(Base):
	__tablename__ = 'stats'
	__table_args__ = (UniqueConstraint('author_id', 'subreddit_id', 'date', 'tag'),)

	id = Column(Integer, primary_key=True)
	author_id = Column(Integer, ForeignKey('users.id'), nullable=False)
	subreddit_id = Column(Integer, ForeignKey('subreddits.id'), nullable=False)
	date = Column(Date, nullable=False)
	count_subscriptions = Column(Integer, nullable=False)
	tag = Column(String(200, collation="NOCASE"))

	author = relationship("User", lazy="joined")
	subreddit = relationship("Subreddit", lazy="joined")

	def __init__(
		self,
		author,
		subreddit,
		date,
		count_subscriptions,
		tag=None
	):
		self.author = author
		self.subreddit = subreddit
		self.date = date
		self.count_subscriptions = count_subscriptions
		self.tag = tag

	def __str__(self):
		return \
			f"u/{self.author.name} r/{self.subreddit.name} : {self.date} : {self.count_subscriptions}" \
			f"{(' : '+self.tag if self.tag is not None else '')}"
