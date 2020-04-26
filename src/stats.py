import discord_logging
from collections import defaultdict

log = discord_logging.get_logger()

from classes.stat import Stat


def save_stats_for_day(database, day):
	counts = defaultdict(lambda: defaultdict(int))
	count_subscriptions = 0
	for subscription in database.get_all_subscriptions():
		if subscription.subreddit.is_enabled:
			counts[subscription.subreddit][subscription.author] += 1
			count_subscriptions += 1

	count_authors = 0
	for subreddit in counts:
		for author in counts[subreddit]:
			count_authors += 1
			database.add_stat(
				Stat(
					author=author,
					subreddit=subreddit,
					date=day,
					count_subscriptions=counts[subreddit][author]
				)
			)

	log.info(f"Saved stats for {count_subscriptions} subscriptions across {count_authors} authors in {len(counts)} subreddits")
