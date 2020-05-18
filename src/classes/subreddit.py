from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, Table, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

import utils
from classes.enums import SubredditPromptType


prompt_association_table = Table(
	'prompt_association', Base.metadata,
	Column('subreddit_id', Integer, ForeignKey('subreddits.id')),
	Column('user_id', Integer, ForeignKey('users.id'))
)


class Subreddit(Base):
	__tablename__ = 'subreddits'

	id = Column(Integer, primary_key=True)
	name = Column(String(80, collation="NOCASE"), unique=True)
	is_enabled = Column(Boolean, nullable=False)
	default_recurring = Column(Boolean, nullable=False)
	last_profiled = Column(DateTime(), nullable=False)
	posts_per_hour = Column(Integer)
	last_scanned = Column(DateTime())
	date_enabled = Column(DateTime())
	tag_enabled = Column(Boolean, nullable=False)
	no_comment = Column(Boolean, nullable=False)
	is_banned = Column(Boolean, nullable=False)
	is_blacklisted = Column(Boolean, nullable=False)

	notice_threshold = Column(Integer, nullable=False)
	flair_blacklist = Column(String(300))
	prompt_type = Column(Enum(SubredditPromptType), nullable=False)

	prompt_users = relationship("User", secondary=prompt_association_table, lazy="joined")

	def __init__(
		self,
		name,
		enabled=False,
		default_recurring=False
	):
		self.name = name
		self.is_enabled = enabled
		self.default_recurring = default_recurring
		self.last_profiled = datetime(2010, 1, 1)
		self.tag_enabled = False
		self.notice_threshold = 5

		self.no_comment = False
		self.is_banned = False
		self.prompt_type = SubredditPromptType.NONE
		self.is_blacklisted = False

	def __str__(self):
		return f"r/{self.name} : {self.is_enabled}"

	def get_flair_blacklist(self):
		if self.flair_blacklist is None:
			return None
		output = set()
		for flair in self.flair_blacklist.split(','):
			output.add(flair)
		return output
