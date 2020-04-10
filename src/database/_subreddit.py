import discord_logging
from datetime import datetime
from datetime import timedelta

from classes.subreddit import Subreddit

log = discord_logging.get_logger()


class _DatabaseSubreddit:
	def __init__(self):
		self.session = self.session  # for pycharm linting

	def get_or_add_subreddit(self, subreddit_name, case_is_user_supplied=False):
		log.debug(f"Fetching subreddit by name: {subreddit_name}")
		subreddit = self.session.query(Subreddit)\
			.filter_by(name=subreddit_name)\
			.first()
		if subreddit is None:
			log.debug(f"Creating subreddit: {subreddit_name}")
			subreddit = Subreddit(subreddit_name)
			self.session.add(subreddit)
		else:
			if subreddit.name != subreddit_name and not case_is_user_supplied and subreddit_name != subreddit_name.lower():
				subreddit.name = subreddit_name

		return subreddit

	def get_subreddit(self, subreddit_name):
		log.debug(f"Fetching subreddit by name: {subreddit_name}")
		subreddit = self.session.query(Subreddit)\
			.filter_by(name=subreddit_name)\
			.first()

		return subreddit

	def get_active_subreddits(self):
		log.debug(f"Fetching active subreddits")
		subreddits = self.session.query(Subreddit)\
			.filter(Subreddit.enabled == True)\
			.order_by(Subreddit.post_per_hour)\
			.all()

		return subreddits

	def get_unprofiled_subreddits(self):
		log.debug(f"Fetching subreddits to profile")
		subreddits = self.session.query(Subreddit)\
			.filter(Subreddit.enabled == True)\
			.filter(Subreddit.last_profiled < datetime.utcnow() - timedelta(days=14))\
			.all()

		return subreddits
