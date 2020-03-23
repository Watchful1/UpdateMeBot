from sqlalchemy import Column, ForeignKey, Integer, String, Boolean
from sqlalchemy.orm import relationship
from database import Base


class DbComment(Base):
	__tablename__ = 'comments'

	id = Column(Integer, primary_key=True)
	thread_id = Column(String(12), nullable=False)
	comment_id = Column(String(12), nullable=False)
	subscriber_id = Column(Integer, ForeignKey('users.id'), nullable=False)
	subscribed_to_id = Column(Integer, ForeignKey('users.id'), nullable=False)
	subreddit_id = Column(Integer, ForeignKey('subreddits.id'), nullable=False)
	recurring = Column(Boolean, nullable=False)
	current_count = Column(Integer, nullable=False)

	subscriber = relationship("User", foreign_keys=[subscriber_id])
	subscribed_to = relationship("User", foreign_keys=[subscriber_id])
	subreddit = relationship("Subreddit")

	def __init__(
		self,
		thread_id,
		comment_id,
		subscriber,
		subscribed_to,
		subreddit,
		recurring,
		current_count=1
	):
		self.thread_id = thread_id
		self.comment_id = comment_id
		self.subscriber = subscriber
		self.subscribed_to = subscribed_to
		self.subreddit = subreddit
		self.recurring = recurring
		self.current_count = current_count
