import discord_logging
from datetime import datetime
from datetime import timedelta

log = discord_logging.get_logger(init=True)

import subreddits
from praw_wrapper import reddit_test
from praw_wrapper.reddit_test import RedditObject, Subreddit
import utils
from classes.subscription import Subscription
from classes.enums import SubredditPromptType
from classes.comment import DbComment


def add_new_post_to_sub(reddit, subreddit, delta, author=None, flair=None, title=None, add_comment=False):
	submission = RedditObject(created=utils.datetime_now() - delta, subreddit=subreddit, author=author, flair=flair, title=title)
	subreddit.posts.append(submission)
	reddit.add_submission(submission)


def create_sub_with_posts(database, reddit, subreddit_name, posts, last_scanned=None, posts_per_hour=1, add_comments=False):
	reddit_subreddit = Subreddit(subreddit_name)
	for post in posts:
		if len(post) == 2:
			add_new_post_to_sub(reddit, reddit_subreddit, post[1], post[0], add_comment=add_comments)
		else:
			add_new_post_to_sub(reddit, reddit_subreddit, post[1], post[0], title=post[2], add_comment=add_comments)
	reddit.add_subreddit(reddit_subreddit)
	db_subreddit = database.get_or_add_subreddit(subreddit_name)
	if last_scanned is None:
		last_scanned = utils.datetime_now() - timedelta(minutes=30)
	db_subreddit.last_scanned = last_scanned
	db_subreddit.date_enabled = last_scanned
	db_subreddit.is_enabled = True
	db_subreddit.posts_per_hour = posts_per_hour
	database.commit()


def bulk_sub_to(database, subreddit_name, author_name, subscriber_names, recurring=True):
	subreddit = database.get_subreddit(subreddit_name)
	author = database.get_or_add_user(author_name)
	for subscriber_name in subscriber_names:
		user = database.get_or_add_user(subscriber_name)
		database.add_subscription(
			Subscription(
				subscriber=user,
				author=author,
				subreddit=subreddit,
				recurring=recurring
			)
		)
	database.commit()


def test_profile_subreddits(database, reddit):
	reddit_subreddit = reddit_test.Subreddit("Subreddit1")
	add_new_post_to_sub(reddit, reddit_subreddit, timedelta(minutes=5))
	add_new_post_to_sub(reddit, reddit_subreddit, timedelta(minutes=6))
	add_new_post_to_sub(reddit, reddit_subreddit, timedelta(hours=1, minutes=7))
	add_new_post_to_sub(reddit, reddit_subreddit, timedelta(hours=1, minutes=8))
	add_new_post_to_sub(reddit, reddit_subreddit, timedelta(hours=2, minutes=1))
	add_new_post_to_sub(reddit, reddit_subreddit, timedelta(hours=3, minutes=2))
	reddit.add_subreddit(reddit_subreddit)
	post_per_hour, updated_name = subreddits.subreddit_posts_per_hour(reddit, reddit_subreddit.display_name)
	assert post_per_hour == 2


def test_unmute_subreddits(database, reddit):
	db_subreddit = database.get_or_add_subreddit("Subreddit1")
	db_subreddit.is_enabled = False
	db_subreddit.muted_until = utils.datetime_now() - timedelta(hours=1)
	db_subreddit = database.get_or_add_subreddit("Subreddit2")
	db_subreddit.is_enabled = False
	db_subreddit.muted_until = utils.datetime_now() + timedelta(hours=1)
	database.commit()

	subreddits.unmute_subreddits(database)

	db_subreddit = database.get_or_add_subreddit("Subreddit1")
	assert db_subreddit.is_enabled is True
	assert db_subreddit.muted_until is None
	db_subreddit = database.get_or_add_subreddit("Subreddit2")
	assert db_subreddit.is_enabled is False
	assert db_subreddit.muted_until is not None


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

	add_new_post_to_sub(reddit, reddit.subreddits["Subreddit1"], timedelta(minutes=2), "Author1")
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
	add_new_post_to_sub(reddit, reddit_subreddit, timedelta(minutes=5), "Author1", flair="meta")
	add_new_post_to_sub(reddit, reddit_subreddit, timedelta(minutes=6), "Author2")
	reddit.add_subreddit(reddit_subreddit)
	db_subreddit = database.get_or_add_subreddit("Subreddit1")
	db_subreddit.last_scanned = utils.datetime_now() - timedelta(minutes=30)
	db_subreddit.is_enabled = True
	db_subreddit.flair_blacklist = "psa,meta"
	db_subreddit.posts_per_hour = 2
	database.commit()

	bulk_sub_to(database, "Subreddit1", "Author1", ["User1", "User2"])
	bulk_sub_to(database, "Subreddit1", "Author2", ["User2", "User3"])
	subreddits.scan_subreddits(reddit, database)

	notifications = database.get_pending_notifications()
	assert len(notifications) == 2
	assert notifications[0].submission.author.name == "Author2"
	assert notifications[1].submission.author.name == "Author2"


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


def test_scan_subreddit_tag(database, reddit):
	create_sub_with_posts(
		database, reddit, "Subreddit1",
		[
			("Author1", timedelta(minutes=5), "[Story1] part 7"),
			("Author2", timedelta(minutes=7))
		]
	)
	subreddit = database.get_subreddit("Subreddit1")
	subreddit.tag_enabled = True
	author = database.get_or_add_user("Author1")
	database.add_subscription(
		Subscription(
			subscriber=database.get_or_add_user("User1"),
			author=author,
			subreddit=subreddit,
			recurring=True,
			tag="Story1"
		)
	)
	database.add_subscription(
		Subscription(
			subscriber=database.get_or_add_user("User2"),
			author=author,
			subreddit=subreddit,
			recurring=True,
			tag="Story2"
		)
	)
	database.add_subscription(
		Subscription(
			subscriber=database.get_or_add_user("User3"),
			author=author,
			subreddit=subreddit,
			recurring=True
		)
	)
	database.commit()
	subreddits.scan_subreddits(reddit, database)

	notifications = database.get_pending_notifications()
	assert len(notifications) == 2
	assert notifications[0].subscription.subscriber.name == "User1"
	assert notifications[1].subscription.subscriber.name == "User3"


def test_scan_single_all_subscription_subreddit(database, reddit):
	create_sub_with_posts(
		database, reddit, "Subreddit1",
		[
			("Author1", timedelta(minutes=5)),
			("Author2", timedelta(minutes=6))
		]
	)
	bulk_sub_to(
		database, "Subreddit1", "Author1",
		["User2"]
	)
	bulk_sub_to(
		database, "Subreddit1", "Author2",
		["User3"]
	)
	subreddit = database.get_subreddit("Subreddit1")
	user = database.get_or_add_user("User1")
	database.add_subscription(
		Subscription(
			subscriber=user,
			author=None,
			subreddit=subreddit,
			recurring=True
		)
	)
	database.commit()
	subreddits.scan_subreddits(reddit, database)

	notifications = database.get_pending_notifications()
	assert len(notifications) == 4
	assert notifications[0].subscription.subscriber.name == "User3"
	assert notifications[1].subscription.subscriber.name == "User1"
	assert notifications[2].subscription.subscriber.name == "User2"
	assert notifications[3].subscription.subscriber.name == "User1"


def test_scan_single_subreddit_multiple_times_same_author(database, reddit):
	create_sub_with_posts(
		database, reddit, "Subreddit1",
		[
			("Author1", timedelta(minutes=5))
		]
	)
	bulk_sub_to(
		database, "Subreddit1", "Author1",
		["User1"],
		False
	)
	bulk_sub_to(
		database, "Subreddit1", "Author1", ["User2"]
	)

	subreddits.scan_subreddits(reddit, database)
	assert len(database.get_pending_notifications()) == 2

	add_new_post_to_sub(reddit, reddit.subreddits["Subreddit1"], timedelta(minutes=2), "Author1")
	subreddits.scan_subreddits(reddit, database)

	notifications = database.get_pending_notifications()
	assert len(notifications) == 3


def test_rescan_update_title(database, reddit):
	create_sub_with_posts(
		database, reddit, "Subreddit1",
		[
			("Author1", timedelta(minutes=5))
		]
	)
	subreddits.scan_subreddits(reddit, database)
	assert len(database.get_all_submissions()) == 1
	db_submission = database.get_all_submissions()[0]
	assert db_submission.rescanned is False
	assert db_submission.title is None
	db_submission.messages_sent = 1
	db_submission.time_created = utils.datetime_now() - timedelta(hours=25)
	database.commit()

	reddit_submission = list(reddit.all_submissions.values())[0]
	reddit_submission.set_title("Test title")
	subreddits.recheck_submissions(reddit, database)

	db_submission = database.get_all_submissions()[0]
	assert db_submission.rescanned is True
	assert db_submission.title == "Test title"


def test_rescan_delete(database, reddit):
	create_sub_with_posts(
		database, reddit, "Subreddit1",
		[
			("Author1", timedelta(minutes=5))
		]
	)
	subreddits.scan_subreddits(reddit, database)
	assert len(database.get_all_submissions()) == 1
	db_submission = database.get_all_submissions()[0]
	db_submission.messages_sent = 1
	db_submission.time_created = utils.datetime_now() - timedelta(hours=25)
	database.commit()

	reddit_submission = list(reddit.all_submissions.values())[0]
	reddit_submission.set_removed_by_category("deleted")
	subreddits.recheck_submissions(reddit, database)

	assert len(database.get_all_submissions()) == 0


def test_rescan_delete_notifications(database, reddit):
	create_sub_with_posts(
		database, reddit, "Subreddit1",
		[
			("Author1", timedelta(minutes=5)),
			("Author2", timedelta(minutes=5))
		],
		add_comments=True
	)
	users = []
	for i in range(35):
		users.append(f"User{i}")
	bulk_sub_to(
		database, "Subreddit1", "Author1",
		users,
		False
	)
	subreddits.scan_subreddits(reddit, database)

	for db_submission in database.get_all_submissions():
		comment_author = "Commenter" + db_submission.author.name
		reddit_comment = reddit_test.RedditObject(
			author=comment_author,
			link_id=db_submission.submission_id
		)
		database.add_comment(
			DbComment(
				comment_id=reddit_comment.id,
				submission=db_submission,
				subscriber=database.get_or_add_user(comment_author),
				author=db_submission.author,
				subreddit=db_submission.subreddit,
				recurring=True
			)
		)
	database.commit()

	assert len(database.get_all_submissions()) == 2
	assert len(database.get_pending_notifications()) == 35
	assert len(database.get_all_comments()) == 2

	reddit_submission = list(reddit.all_submissions.values())[0]
	reddit_submission.set_removed_by_category("deleted")
	subreddits.recheck_submissions(reddit, database)

	# assert len(database.get_all_submissions()) == 1
	# assert len(database.get_pending_notifications()) == 0
	# assert len(database.get_all_comments()) == 1

