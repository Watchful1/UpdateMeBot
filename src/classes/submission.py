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
	url = Column(String(200), nullable=False)
	messages_sent = Column(Integer, nullable=False)
	subreddit_id = Column(Integer, ForeignKey('subreddits.id'), nullable=False)

	comment = relationship("DbComment", uselist=False, back_populates="submission", lazy="joined")
	subreddit = relationship("Subreddit", lazy="joined")

	def __init__(
		self,
		submission_id,
		time_created,
		author_name,
		subreddit,
		permalink
	):
		self.submission_id = submission_id
		self.time_created = time_created
		self.time_scanned = utils.datetime_now()
		self.author_name = author_name
		self.subreddit = subreddit
		self.url = "https://www.reddit.com" + permalink
		self.messages_sent = 0

	def __str__(self):
		return f"u/{self.author_name} to r/{self.subreddit.name} : u/{self.submission_id}"
