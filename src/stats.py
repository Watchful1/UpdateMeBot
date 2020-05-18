import discord_logging
from collections import defaultdict

log = discord_logging.get_logger()

import static
from classes.stat import Stat


def save_stats_for_day(database, day):
	all_counts = defaultdict(lambda: defaultdict(int))
	tag_counts = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
	combined_users = defaultdict(lambda: defaultdict(set))
	count_subscriptions = 0
	for subscription in database.get_all_subscriptions():
		if subscription.subreddit.is_enabled and subscription.subreddit.default_recurring and subscription.author is not None:
			if subscription.tag is not None:
				tag_counts[subscription.subreddit][subscription.author][subscription.tag] += 1
			else:
				all_counts[subscription.subreddit][subscription.author] += 1
			combined_users[subscription.subreddit][subscription.author].add(subscription.subscriber.name)
			count_subscriptions += 1

	count_authors = 0
	for subreddit in all_counts:
		for author in all_counts[subreddit]:
			count_subs = all_counts[subreddit][author]
			if count_subs >= static.STAT_MINIMUM:
				count_authors += 1
				database.add_stat(
					Stat(
						author=author,
						subreddit=subreddit,
						date=day,
						count_subscriptions=count_subs
					)
				)
	for subreddit in tag_counts:
		for author in tag_counts[subreddit]:
			for tag in tag_counts[subreddit][author]:
				count_subs = tag_counts[subreddit][author][tag]
				if count_subs >= static.STAT_MINIMUM:
					database.add_stat(
						Stat(
							author=author,
							subreddit=subreddit,
							date=day,
							count_subscriptions=count_subs,
							tag=tag
						)
					)
			count_subs = len(combined_users[subreddit][author])
			if count_subs >= static.STAT_MINIMUM:
				database.add_stat(
					Stat(
						author=author,
						subreddit=subreddit,
						date=day,
						count_subscriptions=count_subs,
						tag="combined_users"
					)
				)

	log.info(
		f"Saved stats for {count_subscriptions} subscriptions across {count_authors} authors in {len(all_counts)} "
		f"subreddits")
	database.commit()
