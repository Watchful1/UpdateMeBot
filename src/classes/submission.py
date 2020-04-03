from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from database import Base
from datetime import datetime
from sqlalchemy.orm import relationship

import utils


class Submission(Base):
	__tablename__ = 'submissions'

	distinct

	id = Column(Integer, primary_key=True)
	submission_id = Column(String(12), nullable=False)
	time_scanned = Column(DateTime(), nullable=False)
	author_name = Column(String(80), nullable=False)
	subreddit_id = Column(Integer, ForeignKey('subreddits.id'), nullable=False)

	subreddit = relationship("Subreddit")

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
