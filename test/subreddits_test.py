import discord_logging
from datetime import datetime
from datetime import timedelta

log = discord_logging.get_logger(init=True)

import subreddits
import reddit_test
import utils
from reddit_test import RedditObject
from reddit_test import Subreddit
from classes.subscription import Subscription
from classes.enums import SubredditPromptType


def add_new_post_to_sub(subreddit, delta, author=None, flair=None):
	subreddit.posts.append(
		RedditObject(created=utils.datetime_now() - delta, subreddit=subreddit, author=author, flair=flair)
	)


def create_sub_with_posts(database, reddit, subreddit_name, posts, last_scanned=None, posts_per_hour=1):
	reddit_subreddit = Subreddit(subreddit_name)
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
	subreddits.scan_subreddits(reddit, database)

	notifications = database.get_pending_notifications()
	assert len(notifications) == 4
	assert notifications[0].subscription.subscriber.name == "User2"
	assert notifications[1].subscription.subscriber.name == "User3"
	assert notifications[2].subscription.subscriber.name == "User1"
	assert notifications[3].subscription.subscriber.name == "User2"


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
	subreddits.scan_subreddits(reddit, database)
	database.clear_all_notifications()

	add_new_post_to_sub(reddit.subreddits["Subreddit1"], timedelta(minutes=2), "Author1")
	subreddits.scan_subreddits(reddit, database)

	notifications = database.get_pending_notifications()
	assert len(notifications) == 2
	assert notifications[0].subscription.subscriber.name == "User1"
	assert notifications[1].subscription.subscriber.name == "User2"


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
	subreddits.scan_subreddits(reddit, database)

	notifications = database.get_pending_notifications()
	assert len(notifications) == 2


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
	subreddits.scan_subreddits(reddit, database)

	notifications = database.get_pending_notifications()
	assert len(notifications) == 2


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
	subreddits.scan_subreddits(reddit, database)

	notifications = database.get_pending_notifications()
	assert len(notifications) == 2


def test_scan_subreddit_flair_blacklist(database, reddit):
	reddit_subreddit = Subreddit("Subreddit1")
	add_new_post_to_sub(reddit_subreddit, timedelta(minutes=5), "Author1", flair="meta")
	add_new_post_to_sub(reddit_subreddit, timedelta(minutes=6), "Author2")
	reddit.add_subreddit(reddit_subreddit)
	db_subreddit = database.get_or_add_subreddit("Subreddit1")
	db_subreddit.last_scanned = utils.datetime_now() - timedelta(minutes=30)
	db_subreddit.enabled = True
	db_subreddit.flair_blacklist = "psa,meta"
	db_subreddit.post_per_hour = 2
	database.commit()

	bulk_sub_to(database, "Subreddit1", "Author1", ["User1", "User2"])
	bulk_sub_to(database, "Subreddit1", "Author2", ["User2", "User3"])
	subreddits.scan_subreddits(reddit, database)

	notifications = database.get_pending_notifications()
	assert len(notifications) == 2
	assert notifications[0].submission.author_name == "Author2"
	assert notifications[1].submission.author_name == "Author2"


def test_scan_subreddit_post_prompt_all(database, reddit):
	create_sub_with_posts(
		database, reddit, "Subreddit1",
		[
			("Author1", timedelta(minutes=5)),
			("Author2", timedelta(minutes=7))
		]
	)
	db_subreddit = database.get_or_add_subreddit("Subreddit1")
	db_subreddit.prompt_type = SubredditPromptType.ALL
	database.commit()
	subreddits.scan_subreddits(reddit, database)

	assert len(reddit.subreddits["Subreddit1"].posts[0].children) == 1
	assert len(reddit.subreddits["Subreddit1"].posts[1].children) == 1
	assert "and receive a message every" in reddit.subreddits["Subreddit1"].posts[0].children[0].body
	assert "Subreddit1" in reddit.subreddits["Subreddit1"].posts[0].children[0].body
	assert "u/Author1" in reddit.subreddits["Subreddit1"].posts[0].children[0].body
	assert "and receive a message every" in reddit.subreddits["Subreddit1"].posts[1].children[0].body
	assert "Subreddit1" in reddit.subreddits["Subreddit1"].posts[1].children[0].body
	assert "u/Author2" in reddit.subreddits["Subreddit1"].posts[1].children[0].body


def test_scan_subreddit_post_prompt_specific_author(database, reddit):
	create_sub_with_posts(
		database, reddit, "Subreddit1",
		[
			("Author1", timedelta(minutes=5)),
			("Author2", timedelta(minutes=7))
		]
	)
	author1 = database.get_or_add_user("Author1")
	db_subreddit = database.get_or_add_subreddit("Subreddit1")
	db_subreddit.prompt_type = SubredditPromptType.ALLOWED
	db_subreddit.prompt_users.append(author1)
	database.commit()
	subreddits.scan_subreddits(reddit, database)

	assert len(reddit.subreddits["Subreddit1"].posts[0].children) == 1
	assert len(reddit.subreddits["Subreddit1"].posts[1].children) == 0
	assert "and receive a message every" in reddit.subreddits["Subreddit1"].posts[0].children[0].body
	assert "Subreddit1" in reddit.subreddits["Subreddit1"].posts[0].children[0].body
	assert "u/Author1" in reddit.subreddits["Subreddit1"].posts[0].children[0].body
