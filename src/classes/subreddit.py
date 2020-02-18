from sqlalchemy import Column, Integer, String, Boolean, func
from database import Base


class Subreddit(Base):
	__tablename__ = 'subreddits'

	id = Column(Integer, primary_key=True)
	name = Column(String(80), unique=True)
	enabled = Column(Boolean, nullable=False)
	default_recurring = Column(Boolean, nullable=False)
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
		self.no_comment = no_comment
		self.blocked = blocked
