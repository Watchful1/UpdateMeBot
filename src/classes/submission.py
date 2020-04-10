from sqlalchemy import Column, Integer, String,  DateTime, ForeignKey
from database import Base
from sqlalchemy.orm import relationship

import utils


class Submission(Base):
	__tablename__ = 'submissions'

	id = Column(Integer, primary_key=True)
	submission_id = Column(String(12), nullable=False, unique=True)
	time_scanned = Column(DateTime(), nullable=False)
	time_created = Column(DateTime(), nullable=False)
	author_name = Column(String(80), nullable=False)
	subreddit_id = Column(Integer, ForeignKey('subreddits.id'), nullable=False)

	subreddit = relationship("Subreddit")

	def __init__(
		self,
		submission_id,
		time_created,
		author_name,
		subreddit
	):
		self.submission_id = submission_id
		self.time_created = time_created
		self.time_scanned = utils.datetime_now()
		self.author_name = author_name
		self.subreddit = subreddit