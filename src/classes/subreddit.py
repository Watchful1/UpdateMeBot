from sqlalchemy import Column, Integer, String, Boolean, DateTime
from database import Base
from datetime import datetime

import utils


class Subreddit(Base):
	__tablename__ = 'subreddits'

	id = Column(Integer, primary_key=True)
	name = Column(String(80, collation="NOCASE"), unique=True)
	enabled = Column(Boolean, nullable=False)
	default_recurring = Column(Boolean, nullable=False)
	last_profiled = Column(DateTime(), nullable=False)
	post_per_hour = Column(Integer)
	last_scanned = Column(DateTime(), nullable=False)

	no_comment = Column(Boolean, nullable=False)
	blocked = Column(Boolean, nullable=False)

	def __init__(
		self,
		name,
		enabled=False,
		default_recurring=False,
		no_comment=False,
		blocked=False
	):
		self.name = name
		self.enabled = enabled
		self.default_recurring = default_recurring
		self.last_profiled = datetime(2010, 1, 1)
		self.last_scanned = utils.datetime_now()

		self.no_comment = no_comment
		self.blocked = blocked
