import discord_logging
from datetime import datetime
from datetime import timedelta

from classes.subreddit import Subreddit

log = discord_logging.get_logger()


class _DatabaseSubreddit:
	def __init__(self):
		self.session = self.session  # for pycharm linting
		self.log_debug = self.log_debug

	def get_or_add_subreddit(self, subreddit_name, case_is_user_supplied=False, enable_subreddit_if_new=False):
		if self.log_debug:
			log.debug(f"Fetching subreddit by name: {subreddit_name}")
		subreddit = self.session.query(Subreddit)\
			.filter_by(name=subreddit_name)\
			.first()
		if subreddit is None:
			if self.log_debug:
				log.debug(f"Creating subreddit: {subreddit_name}")
			subreddit = Subreddit(subreddit_name, enabled=enable_subreddit_if_new)
			self.session.add(subreddit)
		else:
			if subreddit.name != subreddit_name and not case_is_user_supplied and subreddit_name != subreddit_name.lower():
				subreddit.name = subreddit_name

		return subreddit

	def get_subreddit(self, subreddit_name):
		if self.log_debug:
			log.debug(f"Fetching subreddit by name: {subreddit_name}")
		subreddit = self.session.query(Subreddit)\
			.filter_by(name=subreddit_name)\
			.first()

		return subreddit

	def get_active_subreddits(self):
		if self.log_debug:
			log.debug(f"Fetching active subreddits")
		subreddits = self.session.query(Subreddit)\
			.filter(Subreddit.is_enabled == True)\
			.order_by(Subreddit.posts_per_hour)\
			.all()

		return subreddits

	def get_all_subreddits(self):
		if self.log_debug:
			log.debug(f"Fetching all subreddits")
		subreddits = self.session.query(Subreddit)\
			.all()

		return subreddits

	def get_unprofiled_subreddits(self, limit=10):
		if self.log_debug:
			log.debug(f"Fetching subreddits to profile")
		subreddits = self.session.query(Subreddit)\
			.filter(Subreddit.is_enabled == True)\
			.filter(Subreddit.is_blacklisted == False)\
			.filter(Subreddit.last_profiled < datetime.utcnow() - timedelta(days=30))\
			.all()
		subreddits.extend(
			self.session.query(Subreddit)
			.filter(Subreddit.is_enabled == False)
			.filter(Subreddit.is_blacklisted == False)\
			.filter(Subreddit.last_profiled < datetime.utcnow() - timedelta(days=90))
			.all()
		)

		return subreddits[:limit]

	def get_unmute_subreddits(self):
		if self.log_debug:
			log.debug(f"Fetching subreddits to unmute")
		subreddits = self.session.query(Subreddit)\
			.filter(Subreddit.muted_until != None)\
			.filter(Subreddit.muted_until < datetime.utcnow())\
			.all()

		return subreddits

	def get_count_all_subreddits(self):
		return self.session.query(Subreddit).count()
