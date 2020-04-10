import discord_logging
from datetime import datetime
from datetime import timedelta

log = discord_logging.get_logger(init=True)

import subreddits
import reddit_test
import utils
from reddit_test import RedditObject
from classes.subscription import Subscription


def add_new_post_to_sub(subreddit, delta, author=None):
	subreddit.posts.append(RedditObject(created=utils.datetime_now() - delta, subreddit=subreddit, author=author))


def create_sub_with_posts(database, reddit, subreddit_name, posts, last_scanned=None, posts_per_hour=1):
	reddit_subreddit = reddit_test.Subreddit(subreddit_name)
	for post in posts:
		add_new_post_to_sub(reddit_subreddit, post[1], post[0])
	reddit.add_subreddit(reddit_subreddit)
	db_subreddit = database.get_or_add_subreddit(subreddit_name)
	if last_scanned is None:
		last_scanned = utils.datetime_now() - timedelta(minutes=30)
	db_subreddit.last_scanned = last_scanned
	db_subreddit.enabled = True
	db_subreddit.post_per_hour = posts_per_hour
	database.commit()


def bulk_sub_to(database, subreddit_name, author_name, subscriber_names):
	subreddit = database.get_subreddit(subreddit_name)
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


def test_profile_subreddits(database, reddit):
	reddit_subreddit = reddit_test.Subreddit("Subreddit1")
	add_new_post_to_sub(reddit_subreddit, timedelta(minutes=5))
	add_new_post_to_sub(reddit_subreddit, timedelta(minutes=6))
	add_new_post_to_sub(reddit_subreddit, timedelta(hours=1, minutes=7))
	add_new_post_to_sub(reddit_subreddit, timedelta(hours=1, minutes=8))
	add_new_post_to_sub(reddit_subreddit, timedelta(hours=2, minutes=1))
	add_new_post_to_sub(reddit_subreddit, timedelta(hours=3, minutes=2))
	reddit.add_subreddit(reddit_subreddit)
	assert subreddits.subreddit_posts_per_hour(reddit, reddit_subreddit.display_name) == 2


def test_scan_single_subreddit(database, reddit):
	create_sub_with_posts(
		database, reddit, "Subreddit1",
		[
			("Author1", timedelta(minutes=5)),
			("Author2", timedelta(minutes=6))
		]
	)
	bulk_sub_to(
		database, "Subreddit1", "Author1",
		["User1", "User2"]
	)
	bulk_sub_to(
		database, "Subreddit1", "Author2",
		["User2", "User3"]
	)
	subreddits.scan_subreddits(database, reddit)

	messages = database.get_all_pending_messages()
	assert len(messages) == 4
	assert messages[0].subscription.subscriber.name == "User2"
	assert messages[1].subscription.subscriber.name == "User3"
	assert messages[2].subscription.subscriber.name == "User1"
	assert messages[3].subscription.subscriber.name == "User2"


def test_scan_single_subreddit_multiple_times(database, reddit):
	create_sub_with_posts(
		database, reddit, "Subreddit1",
		[
			("Author1", timedelta(minutes=5)),
			("Author2", timedelta(minutes=6))
		]
	)
	bulk_sub_to(
		database, "Subreddit1", "Author1",
		["User1", "User2"]
	)
	bulk_sub_to(
		database, "Subreddit1", "Author2",
		["User2", "User3"]
	)
	subreddits.scan_subreddits(database, reddit)
	database.clear_all_messages()

	add_new_post_to_sub(reddit.subreddits["Subreddit1"], timedelta(minutes=2), "Author1")
	subreddits.scan_subreddits(database, reddit)

	messages = database.get_all_pending_messages()
	assert len(messages) == 2
	assert messages[0].subscription.subscriber.name == "User1"
	assert messages[1].subscription.subscriber.name == "User2"


def test_scan_multiple_subreddits(database, reddit):
	create_sub_with_posts(
		database, reddit, "Subreddit1",
		[
			("Author1", timedelta(minutes=5)),
			("Author2", timedelta(minutes=7))
		]
	)
	create_sub_with_posts(
		database, reddit, "Subreddit2",
		[
			("Author2", timedelta(minutes=6)),
			("Author3", timedelta(minutes=8))
		]
	)
	bulk_sub_to(database, "Subreddit1", "Author1", ["User1"])
	bulk_sub_to(database, "Subreddit2", "Author3", ["User1"])
	subreddits.scan_subreddits(database, reddit)

	messages = database.get_all_pending_messages()
	assert len(messages) == 2


def test_scan_multiple_subreddit_groups(database, reddit):
	create_sub_with_posts(
		database, reddit, "Subreddit1",
		[
			("Author1", timedelta(minutes=5)),
			("Author2", timedelta(minutes=7))
		],
		posts_per_hour=30
	)
	create_sub_with_posts(
		database, reddit, "Subreddit2",
		[
			("Author2", timedelta(minutes=6)),
			("Author3", timedelta(minutes=8))
		],
		posts_per_hour=30
	)
	bulk_sub_to(database, "Subreddit1", "Author1", ["User1"])
	bulk_sub_to(database, "Subreddit2", "Author3", ["User1"])
	subreddits.scan_subreddits(database, reddit)

	messages = database.get_all_pending_messages()
	assert len(messages) == 2


def test_scan_multiple_subreddits_split(database, reddit):
	create_sub_with_posts(
		database, reddit, "Subreddit1",
		[
			("Author1", timedelta(minutes=5)),
			("Author2", timedelta(minutes=7))
		]
	)
	create_sub_with_posts(
		database, reddit, "Subreddit2",
		[
			("Author2", timedelta(minutes=6)),
			("Author3", timedelta(minutes=8))
		],
		last_scanned=utils.datetime_now() - timedelta(hours=2)
	)
	bulk_sub_to(database, "Subreddit1", "Author1", ["User1"])
	bulk_sub_to(database, "Subreddit2", "Author3", ["User1"])
	subreddits.scan_subreddits(database, reddit)

	messages = database.get_all_pending_messages()
	assert len(messages) == 2
