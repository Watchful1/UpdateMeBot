import discord_logging
from datetime import date, timedelta

log = discord_logging.get_logger(init=True)

import stats
import utils
from classes.subscription import Subscription


def bulk_sub_to(database, subreddit_name, author_name, subscriber_names):
	subreddit = database.get_or_add_subreddit(subreddit_name)
	author = database.get_or_add_user(author_name)
	for subscriber_name in subscriber_names:
		user = database.get_or_add_user(subscriber_name)
		database.add_subscription(
			Subscription(
				subscriber=user,
				author=author,
				subreddit=subreddit,
				recurring=True
			)
		)
	database.commit()


def test_save_single_day_stats(database, reddit):
	date_now = date(2020, 1, 1)
	bulk_sub_to(
		database, "Subreddit1", "Author1",
		["User1", "User2", "User3", "User4", "User5", "User6"]
	)
	bulk_sub_to(
		database, "Subreddit1", "Author2",
		["User2", "User3", "User4"]
	)
	bulk_sub_to(
		database, "Subreddit2", "Author2",
		["User6", "User7"]
	)
	bulk_sub_to(
		database, "Subreddit3", "Author3",
		["User3", "User9"]
	)
	stats.save_stats_for_day(database, date_now)

	stats_1_1 = database.get_recent_stats_for_author_subreddit(
		database.get_or_add_user("Author1"),
		database.get_or_add_subreddit("Subreddit1")
	)
	assert len(stats_1_1) == 1
	assert stats_1_1[0].author.name == "Author1"
	assert stats_1_1[0].subreddit.name == "Subreddit1"
	assert stats_1_1[0].date == date_now
	assert stats_1_1[0].count_subscriptions == 6

	stats_2_1 = database.get_recent_stats_for_author_subreddit(
		database.get_or_add_user("Author2"),
		database.get_or_add_subreddit("Subreddit1")
	)
	assert stats_2_1[0].count_subscriptions == 3

	stats_2_2 = database.get_recent_stats_for_author_subreddit(
		database.get_or_add_user("Author2"),
		database.get_or_add_subreddit("Subreddit2")
	)
	assert stats_2_2[0].count_subscriptions == 2

	stats_3_3 = database.get_recent_stats_for_author_subreddit(
		database.get_or_add_user("Author3"),
		database.get_or_add_subreddit("Subreddit3")
	)
	assert stats_3_3[0].count_subscriptions == 2


def test_save_multi_day_stats(database, reddit):
	date_now = date(2020, 1, 10)
	bulk_sub_to(
		database, "Subreddit1", "Author1",
		["User1", "User2", "User3", "User4", "User5", "User6"]
	)
	stats.save_stats_for_day(database, date_now - timedelta(days=5))
	database.delete_user_subscriptions(database.get_or_add_user("User2"))
	stats.save_stats_for_day(database, date_now - timedelta(days=4))
	bulk_sub_to(
		database, "Subreddit1", "Author1",
		["User8", "User9"]
	)
	stats.save_stats_for_day(database, date_now - timedelta(days=3))
	stats.save_stats_for_day(database, date_now - timedelta(days=2))
	bulk_sub_to(
		database, "Subreddit1", "Author1",
		["User10"]
	)
	stats.save_stats_for_day(database, date_now - timedelta(days=1))
	bulk_sub_to(
		database, "Subreddit1", "Author1",
		["User11", "User12", "User13"]
	)
	stats.save_stats_for_day(database, date_now)

	stats_1_1 = database.get_recent_stats_for_author_subreddit(
		database.get_or_add_user("Author1"),
		database.get_or_add_subreddit("Subreddit1")
	)
	assert len(stats_1_1) == 6
	assert stats_1_1[0].author.name == "Author1"
	assert stats_1_1[0].subreddit.name == "Subreddit1"
	assert stats_1_1[0].date == date_now
	assert stats_1_1[0].count_subscriptions == 11
	assert stats_1_1[1].date == date_now - timedelta(days=1)
	assert stats_1_1[1].count_subscriptions == 8
	assert stats_1_1[2].date == date_now - timedelta(days=2)
	assert stats_1_1[2].count_subscriptions == 7
	assert stats_1_1[3].date == date_now - timedelta(days=3)
	assert stats_1_1[3].count_subscriptions == 7
	assert stats_1_1[4].date == date_now - timedelta(days=4)
	assert stats_1_1[4].count_subscriptions == 5
	assert stats_1_1[5].date == date_now - timedelta(days=5)
	assert stats_1_1[5].count_subscriptions == 6
