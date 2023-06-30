from sqlalchemy import Column, String, Integer, Boolean, DateTime
from database import Base


class User(Base):
	__tablename__ = 'users'

	id = Column(Integer, primary_key=True)
	name = Column(String(80, collation="NOCASE"), nullable=False, unique=True)
	short_notifs = Column(Boolean, nullable=False, default=False)
	first_failure = Column(DateTime())

	def __init__(
		self,
		name
	):
		self.name = name
		self.short_notifs = False

	def __str__(self):
		return f"u/{self.name}"
