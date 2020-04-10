from sqlalchemy import Column, Integer, String,  DateTime, ForeignKey
from database import Base
from sqlalchemy.orm import relationship

import utils


class Message(Base):
	__tablename__ = 'messages'

	id = Column(Integer, primary_key=True)
	subscription_id = Column(Integer, ForeignKey('subscriptions.id'), nullable=False)
	submission_id = Column(Integer, ForeignKey('submissions.id'), nullable=False)

	subscription = relationship("Subscription", foreign_keys=[subscription_id])
	submission = relationship("Submission", foreign_keys=[submission_id])

	def __init__(
		self,
		subscription,
		submission
	):
		self.subscription = subscription
		self.submission = submission
