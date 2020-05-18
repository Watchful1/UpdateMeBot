import discord_logging

log = discord_logging.init_logging()

import utils
from database import Database
from classes.stat import Stat
from classes.subscription import Subscription

database = Database()

# delete stats under 10
log.info(f"Cleaning up stats")

stats_total = database.session.query(Stat).count()
stats_deleted = database.session.query(Stat).filter(Stat.count_subscriptions < 10).delete(synchronize_session='fetch')
stats_remaining = database.session.query(Stat).count()

log.info(f"Deleted {stats_deleted:,} of {stats_total:,} stats")
log.info(f"{stats_deleted:,} + {stats_remaining:,} = {stats_deleted + stats_remaining:,} : {stats_deleted + stats_remaining == stats_total}")

database.commit()
database.session.execute("VACUUM")
database.commit()

subreddits_to_blacklist = ['WritingPrompts', 'AskReddit', 'whatisthisthing', 'bestoflegaladvice', 'AskHistorians', 'RequestABot']
for subreddit_name in subreddits_to_blacklist:
	subreddit = database.get_subreddit(subreddit_name)
	count_subscriptions = database.session.query(Subscription).filter(Subscription.subreddit == subreddit).delete()
	count_stats = database.session.query(Stat).filter(Stat.subreddit == subreddit).delete()
	subreddit.is_blacklisted = True
	database.commit()
	log.info(f"r/{subreddit_name} blacklisted, {count_subscriptions} subscriptions and {count_stats} stats deleted")

subreddits_to_delete = ['subreddit', 'RequestABot', 'Overwatch', 'amistories', 'Darkland', 'John_writes', 'jsgunn', 'SubTestBot2', 'TwentyNinetyNine', 'EdgarAllanHobo', 'GigaWrites', 'pirates']
for subreddit_name in subreddits_to_delete:
	subreddit = database.get_subreddit(subreddit_name)
	count_subscriptions = database.session.query(Subscription).filter(Subscription.subreddit == subreddit).delete()
	count_stats = database.session.query(Stat).filter(Stat.subreddit == subreddit).delete()
	database.session.delete(subreddit)
	database.commit()
	log.info(f"r/{subreddit_name} deleted, {count_subscriptions} subscriptions and {count_stats} stats deleted")

subreddits_to_activate_subscribe = ['IsTodayFridayThe13th', 'imsorryjon', 'redditserials', 'eroticliterature']
for subreddit_name in subreddits_to_activate_subscribe:
	subreddit = database.get_subreddit(subreddit_name)
	count_subscriptions = database.get_count_subscriptions_for_subreddit(subreddit)
	subreddit.is_enabled = True
	subreddit.last_scanned = utils.datetime_now()
	subreddit.date_enabled = utils.datetime_now()
	subreddit.default_recurring = True
	if subreddit.posts_per_hour is None:
		subreddit.posts_per_hour = 50
	database.commit()
	log.info(f"Activated r/{subreddit_name} with {count_subscriptions} subscriptions")

subreddits_to_activate_update = ['ProRevenge', 'whatisthisthing', 'JUSTNOMIL', 'entitledparents']
for subreddit_name in subreddits_to_activate_subscribe:
	subreddit = database.get_subreddit(subreddit_name)
	count_subscriptions = database.get_count_subscriptions_for_subreddit(subreddit)
	subreddit.is_enabled = True
	subreddit.last_scanned = utils.datetime_now()
	subreddit.date_enabled = utils.datetime_now()
	subreddit.default_recurring = False
	if subreddit.posts_per_hour is None:
		subreddit.posts_per_hour = 50
	database.commit()
	log.info(f"Activated r/{subreddit_name} with {count_subscriptions} subscriptions")

user = database.get_user('nosleepautobot')
count_subscriptions = database.session.query(Subscription).filter(Subscription.subscriber == user).delete()
log.info(f"u/{user.name} deleted, {count_subscriptions} subscriptions deleted")

database.commit()
database.session.execute("VACUUM")

database.clean()

database.close()
