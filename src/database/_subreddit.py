import discord_logging

from classes.subreddit import Subreddit

log = discord_logging.get_logger()


class _DatabaseSubreddit:
	def __init__(self):
		self.session = self.session  # for pycharm linting

	def get_or_add_subreddit(self, subreddit_name):
		log.debug(f"Fetching subreddit by name: {subreddit_name}")
		subreddit = self.session.query(Subreddit)\
			.filter_by(name=subreddit_name)\
			.first()
		if subreddit is None:
			log.debug(f"Creating subreddit: {subreddit_name}")
			subreddit = Subreddit(subreddit_name)
			self.session.add(subreddit)

		return subreddit

	def get_subreddit(self, subreddit_name):
		log.debug(f"Fetching subreddit by name: {subreddit_name}")
		subreddit = self.session.query(Subreddit)\
			.filter_by(name=subreddit_name)\
			.first()

		return subreddit
