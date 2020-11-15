import discord_logging
from datetime import timedelta

log = discord_logging.get_logger(init=True)


import static
import notifications
import utils
from praw_wrapper import reddit_test
from classes.subscription import Subscription
from classes.submission import Submission
from classes.notification import Notification


def get_submission(database, author, subreddit, submission_id, title=None, tag=None, time_created=None):
	submission = database.get_submission_by_id(submission_id)
	if submission is None:
		if time_created is None:
			time_created = utils.datetime_now()
		submission = Submission(
			submission_id=submission_id,
			time_created=time_created,
			author=author,
			subreddit=subreddit,
			permalink=f"/r/{subreddit.name}/comments/{submission_id}/",
			title=title,
			tag=tag
		)
		database.add_submission(submission)
		database.commit()
	return submission


def queue_message(database, subscriber_name, author_name, subreddit_name, submission_id, recurring=True, tag=None):
	subscriber = database.get_or_add_user(subscriber_name)
	author = database.get_or_add_user(author_name)
	subreddit = database.get_or_add_subreddit(subreddit_name, enable_subreddit_if_new=True)
	if tag is not None:
		subreddit.tag_enabled = True
	subscription = database.get_subscription_by_fields(subscriber, author, subreddit, tag)
	if subscription is None:
		subscription = Subscription(
			subscriber=subscriber,
			author=author,
			subreddit=subreddit,
			recurring=recurring,
			tag=tag
		)
		database.add_subscription(subscription)
	submission = get_submission(database, author, subreddit, submission_id, tag=tag)
	database.add_notification(Notification(subscription, submission))
	database.commit()


def assert_message(message, dest_username, contains):
	assert message.dest.name == dest_username
	for contain in contains:
		assert contain in message.body


def test_send_message(database, reddit):
	submission_id = reddit_test.random_id()
	queue_message(database, "Subscriber1", "Author1", "Subreddit1", submission_id)

	assert database.get_count_pending_notifications() == 1
	notifications.send_queued_notifications(reddit, database)
	assert database.get_count_pending_notifications() == 0
	assert len(database.get_user_subscriptions_by_name("Subscriber1", only_enabled=False)) == 1

	assert len(reddit.sent_messages) == 1
	assert_message(
		reddit.sent_messages[0], "Subscriber1", ["u/Author1", "r/Subreddit1", "remove your subscription", submission_id])


def test_send_message_update(database, reddit):
	submission_id = reddit_test.random_id()
	queue_message(database, "Subscriber1", "Author1", "Subreddit1", submission_id, False)

	assert database.get_count_pending_notifications() == 1
	notifications.send_queued_notifications(reddit, database)
	assert database.get_count_pending_notifications() == 0
	assert len(database.get_user_subscriptions_by_name("Subscriber1")) == 0

	assert len(reddit.sent_messages) == 1
	assert_message(
		reddit.sent_messages[0], "Subscriber1",
		[
			"u/Author1", "r/Subreddit1", "if you want to be messaged the next", "if you want to be messaged every",
			submission_id
		])


def test_send_messages(database, reddit):
	static.STAT_MINIMUM = 1
	submission_id1 = reddit_test.random_id()
	submission_id2 = reddit_test.random_id()
	submission_id3 = reddit_test.random_id()
	queue_message(database, "Subscriber1", "Author1", "Subreddit1", submission_id1)
	queue_message(database, "Subscriber2", "Author1", "Subreddit1", submission_id1)
	queue_message(database, "Subscriber1", "Author2", "Subreddit1", submission_id2)
	queue_message(database, "Subscriber3", "Author2", "Subreddit1", submission_id2)
	queue_message(database, "Subscriber2", "Author1", "Subreddit2", submission_id3)
	queue_message(database, "Subscriber3", "Author1", "Subreddit2", submission_id3)
	queue_message(database, "Subscriber4", "Author1", "Subreddit2", submission_id3)
	queue_message(database, "Author1", "Author1", "Subreddit2", submission_id3)

	assert database.get_count_pending_notifications() == 8
	notifications.send_queued_notifications(reddit, database)
	assert database.get_count_pending_notifications() == 0

	assert len(reddit.sent_messages) == 8
	assert_message(reddit.sent_messages[0], "Subscriber1", ["u/Author1", "r/Subreddit1", submission_id1])
	assert_message(reddit.sent_messages[1], "Subscriber2", ["u/Author1", "r/Subreddit1", submission_id1])
	assert_message(reddit.sent_messages[2], "Subscriber1", ["u/Author2", "r/Subreddit1", submission_id2])
	assert_message(reddit.sent_messages[3], "Subscriber3", ["u/Author2", "r/Subreddit1", submission_id2])
	assert_message(reddit.sent_messages[4], "Subscriber2", ["u/Author1", "r/Subreddit2", submission_id3])
	assert_message(reddit.sent_messages[5], "Subscriber3", ["u/Author1", "r/Subreddit2", submission_id3])
	assert_message(reddit.sent_messages[6], "Subscriber4", ["u/Author1", "r/Subreddit2", submission_id3])
	assert_message(
		reddit.sent_messages[7], "Author1",
		["r/Subreddit2", submission_id3, "finished sending out 3 notifications"]
	)


def test_recent_titles(database, reddit):
	author = database.get_or_add_user("Author1")
	subreddit = database.get_or_add_subreddit("Subreddit1", enable_subreddit_if_new=True)
	submission1 = get_submission(
		database, author, subreddit, reddit_test.random_id(), title="Title 1",
		time_created=utils.datetime_now() - timedelta(hours=4))
	submission2 = get_submission(
		database, author, subreddit, reddit_test.random_id(), title="Title 2",
		time_created=utils.datetime_now() - timedelta(hours=3))
	submission3 = get_submission(
		database, author, subreddit, reddit_test.random_id(), title="Title 3",
		time_created=utils.datetime_now() - timedelta(hours=2))
	submission4 = get_submission(
		database, author, subreddit, reddit_test.random_id(), title="Title 4",
		time_created=utils.datetime_now() - timedelta(hours=1))
	submission5 = get_submission(
		database, author, subreddit, reddit_test.random_id(), title="Title 5",
		time_created=utils.datetime_now())

	queue_message(database, "Subscriber1", "Author1", "Subreddit1", submission5.submission_id)
	notifications.send_queued_notifications(reddit, database)

	assert len(reddit.sent_messages) == 1
	body = reddit.sent_messages[0].body
	assert submission1.submission_id not in body
	assert submission2.submission_id in body
	assert submission3.submission_id in body
	assert submission4.submission_id in body
	assert "Title 1" not in body
	assert "Title 2" in body
	assert "Title 3" in body
	assert "Title 4" in body
	assert "Title 5" in body


def test_send_message_tag(database, reddit):
	submission_id = reddit_test.random_id()
	queue_message(database, "Subscriber1", "Author1", "Subreddit1", submission_id, recurring=True, tag="Story1")

	notifications.send_queued_notifications(reddit, database)

	assert len(reddit.sent_messages) == 1
	assert_message(
		reddit.sent_messages[0], "Subscriber1",
		["u/Author1", "r/Subreddit1", "with the tag <Story1>", "remove your subscription for the tag", submission_id]
	)
