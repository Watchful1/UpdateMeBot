from sqlalchemy import Column, String, Integer, Boolean
from database import Base


class User(Base):
	__tablename__ = 'users'

	id = Column(Integer, primary_key=True)
	name = Column(String(80), nullable=False)
	prompt = Column(String(200))
	blocked = Column(Boolean, nullable=False)

	def __init__(
		self,
		name,
		prompt=None,
		blocked=False
	):
		self.name = name
		self.prompt = prompt
		self.blocked = blocked
