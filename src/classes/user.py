from sqlalchemy import Column, String, Integer, Boolean
from database import Base


class User(Base):
	__tablename__ = 'users'

	id = Column(Integer, primary_key=True)
	name = Column(String(80, collation="NOCASE"), nullable=False, unique=True)
	short_notifs = Column(Boolean, nullable=False, default=False)

	def __init__(
		self,
		name
	):
		self.name = name

	def __str__(self):
		return f"u/{self.name}"
