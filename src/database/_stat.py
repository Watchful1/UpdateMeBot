import discord_logging

from classes.stat import Stat

log = discord_logging.get_logger()


class _DatabaseStats:
	def __init__(self):
		self.session = self.session  # for pycharm linting
		self.log_debug = self.log_debug

	def add_stat(self, stat):
		if self.log_debug:
			log.debug(f"Adding stat: {stat}")
		self.session.add(stat)

	def get_recent_stats_for_author_subreddit(self, author, subreddit, tag=None, days=7):
		if self.log_debug:
			log.debug(f"Getting last {days} days of stats for u/{author.name} in r/{subreddit.name}")
		stats = self.session.query(Stat)\
			.filter(Stat.author == author)\
			.filter(Stat.subreddit == subreddit)\
			.filter(Stat.tag == tag)\
			.order_by(Stat.date.desc())\
			.limit(days)\
			.all()

		return stats

	def get_stat_for_author_subreddit_day(self, date, author, subreddit, tag=None):
		if self.log_debug:
			log.debug(f"Getting count subscriptions on {date} for u/{author.name} in r/{subreddit.name}")
		stat = self.session.query(Stat)\
			.filter(Stat.author == author)\
			.filter(Stat.subreddit == subreddit)\
			.filter(Stat.tag == tag)\
			.filter(Stat.date == date)\
			.first()

		return stat

	def get_all_stats_for_day(self, date):
		if self.log_debug:
			log.debug(f"Getting all stats for {date}")
		stats = self.session.query(Stat)\
			.filter(Stat.date == date)\
			.all()

		return stats

	def get_count_stats_for_user(self, user):
		if self.log_debug:
			log.debug(f"Getting count stats for u/{user}")
		return self.session.query(Stat)\
			.filter(Stat.author == user)\
			.count()

	def delete_user_stats(self, user):
		if self.log_debug:
			log.debug(f"Deleting all stats for u/{user.name}")

		return self.session.query(Stat)\
			.filter(Stat.author == user)\
			.delete(synchronize_session='fetch')

	def get_count_all_stats(self):
		return self.session.query(Stat).count()
