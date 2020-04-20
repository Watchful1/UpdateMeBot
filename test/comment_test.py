import discord_logging

log = discord_logging.get_logger(init=True)

import comments
import utils
import static
from reddit_test import RedditObject
from classes.submission import Submission
from classes.subscription import Subscription
from classes.subreddit import Subreddit
from classes.comment import DbComment


def test_process_comment_update(database, reddit):
	subscriber_name = "Subscriber1"
	author_name = "Author1"
	db_subreddit = database.get_or_add_subreddit("TestSub", enable_subreddit_if_new=True)
	comment_id = utils.random_id()
	submission_id = utils.random_id()
	comment = RedditObject(
		body=f"{static.TRIGGER_UPDATE}!",
		author=subscriber_name,
		id=comment_id,
		link_id="t3_"+submission_id,
		permalink=f"/r/test/comments/{submission_id}/_/{comment_id}/",
		subreddit=db_subreddit.name
	)
	db_submission = Submission(
		submission_id=submission_id,
		time_created=utils.datetime_now(),
		author_name=author_name,
		subreddit=db_subreddit,
		permalink=f"/r/{db_subreddit.name}/comments/{submission_id}/"
	)
	database.add_submission(db_submission)
	database.commit()

	reddit.add_comment(comment)

	comments.process_comment(comment.get_pushshift_dict(), reddit, database)
	result = comment.get_first_child().body

	assert "I will message you next time" in result
	assert author_name in result
	assert db_subreddit.name in result
	assert "Click this link" in result

	subscriptions = database.get_user_subscriptions_by_name(subscriber_name)
	assert len(subscriptions) == 1
	assert subscriptions[0].subscriber.name == subscriber_name
	assert subscriptions[0].author.name == author_name
	assert subscriptions[0].subreddit.name == db_subreddit.name
	assert subscriptions[0].recurring is False


def test_process_comment_subscribe(database, reddit):
	subscriber_name = "Subscriber1"
	author_name = "Author1"
	db_subreddit = database.get_or_add_subreddit("TestSub", enable_subreddit_if_new=True)
	comment_id = utils.random_id()
	submission_id = utils.random_id()
	comment = RedditObject(
		body=f"{static.TRIGGER_SUBSCRIBE}!",
		author=subscriber_name,
		id=comment_id,
		link_id="t3_"+submission_id,
		permalink=f"/r/test/comments/{submission_id}/_/{comment_id}/",
		subreddit=db_subreddit.name
	)
	db_submission = Submission(
		submission_id=submission_id,
		time_created=utils.datetime_now(),
		author_name=author_name,
		subreddit=db_subreddit,
		permalink=f"/r/{db_subreddit.name}/comments/{submission_id}/"
	)
	database.add_submission(db_submission)
	database.commit()

	reddit.add_comment(comment)

	comments.process_comment(comment.get_pushshift_dict(), reddit, database)
	result = comment.get_first_child().body

	assert "I will message you each time" in result
	assert author_name in result
	assert db_subreddit.name in result
	assert "Click this link" in result

	subscriptions = database.get_user_subscriptions_by_name(subscriber_name)
	assert len(subscriptions) == 1
	assert subscriptions[0].subscriber.name == subscriber_name
	assert subscriptions[0].author.name == author_name
	assert subscriptions[0].subreddit.name == db_subreddit.name
	assert subscriptions[0].recurring is True


def test_process_comment_subreddit_not_enabled(database, reddit):
	subscriber_name = "Subscriber1"
	author_name = "Author1"
	subreddit_name = "TestSub"
	comment_id = utils.random_id()
	submission_id = utils.random_id()
	comment = RedditObject(
		body=f"{static.TRIGGER_SUBSCRIBE}!",
		author=subscriber_name,
		id=comment_id,
		link_id="t3_"+submission_id,
		permalink=f"/r/test/comments/{submission_id}/_/{comment_id}/",
		subreddit=subreddit_name
	)
	reddit.add_comment(comment)
	reddit.add_submission(RedditObject(id=submission_id, subreddit=subreddit_name, author=author_name))

	comments.process_comment(comment.get_pushshift_dict(), reddit, database)

	assert len(comment.children) == 0

	subscriptions = database.get_user_subscriptions_by_name(subscriber_name)
	assert len(subscriptions) == 1
	assert subscriptions[0].subscriber.name == subscriber_name
	assert subscriptions[0].author.name == author_name
	assert subscriptions[0].subreddit.name == subreddit_name
	assert subscriptions[0].recurring is True

	assert len(reddit.sent_messages) == 1
	assert "is not being tracked by the bot" in reddit.sent_messages[0].body
	assert subreddit_name in reddit.sent_messages[0].body


def test_process_comment_thread_replied(database, reddit):
	subscriber_name = "Subscriber1"
	author_name = "Author1"
	db_subreddit = database.get_or_add_subreddit("TestSub", enable_subreddit_if_new=True)
	comment_id = utils.random_id()
	submission_id = utils.random_id()
	comment = RedditObject(
		body=f"{static.TRIGGER_UPDATE}!",
		author=subscriber_name,
		id=comment_id,
		link_id="t3_"+submission_id,
		permalink=f"/r/test/comments/{submission_id}/_/{comment_id}/",
		subreddit=db_subreddit.name
	)
	reddit.add_comment(comment)
	db_submission = Submission(
		submission_id=submission_id,
		time_created=utils.datetime_now(),
		author_name=author_name,
		subreddit=db_subreddit,
		permalink=f"/r/{db_subreddit.name}/comments/{submission_id}/"
	)
	database.add_submission(db_submission)
	previous_comment = DbComment(
		comment_id=utils.random_id(),
		submission=db_submission,
		subscriber=database.get_or_add_user("Subscriber2"),
		author=database.get_or_add_user(author_name),
		subreddit=db_subreddit,
		recurring=False
	)
	database.add_comment(previous_comment)
	database.commit()

	comments.process_comment(comment.get_pushshift_dict(), reddit, database)

	assert len(comment.children) == 0

	subscriptions = database.get_user_subscriptions_by_name(subscriber_name)
	assert len(subscriptions) == 1
	assert subscriptions[0].subscriber.name == subscriber_name
	assert subscriptions[0].author.name == author_name
	assert subscriptions[0].subreddit.name == db_subreddit.name
	assert subscriptions[0].recurring is False

	assert len(reddit.sent_messages) == 1
	assert "I will message you next" in reddit.sent_messages[0].body
	assert db_subreddit.name in reddit.sent_messages[0].body


def test_process_comment_already_subscribed(database, reddit):
	subscriber_name = "Subscriber1"
	author_name = "Author1"
	db_subreddit = database.get_or_add_subreddit("TestSub", enable_subreddit_if_new=True)
	comment_id = utils.random_id()
	submission_id = utils.random_id()
	comment = RedditObject(
		body=f"{static.TRIGGER_UPDATE}!",
		author=subscriber_name,
		id=comment_id,
		link_id="t3_"+submission_id,
		permalink=f"/r/test/comments/{submission_id}/_/{comment_id}/",
		subreddit=db_subreddit.name
	)
	reddit.add_comment(comment)
	reddit.add_submission(RedditObject(id=submission_id, subreddit=db_subreddit.name, author=author_name))
	database.add_subscription(
		Subscription(
			subscriber=database.get_or_add_user(subscriber_name),
			author=database.get_or_add_user(author_name),
			subreddit=db_subreddit,
			recurring=False
		)
	)

	comments.process_comment(comment.get_pushshift_dict(), reddit, database)

	assert len(comment.children) == 0

	subscriptions = database.get_user_subscriptions_by_name(subscriber_name)
	assert len(subscriptions) == 1

	assert len(reddit.sent_messages) == 1
	assert "You had already asked me to message you" in reddit.sent_messages[0].body
	assert db_subreddit.name in reddit.sent_messages[0].body


def test_process_comment_update_subscription(database, reddit):
	subscriber_name = "Subscriber1"
	author_name = "Author1"
	db_subreddit = database.get_or_add_subreddit("TestSub", enable_subreddit_if_new=True)
	comment_id = utils.random_id()
	submission_id = utils.random_id()
	comment = RedditObject(
		body=f"{static.TRIGGER_UPDATE}!",
		author=subscriber_name,
		id=comment_id,
		link_id="t3_"+submission_id,
		permalink=f"/r/test/comments/{submission_id}/_/{comment_id}/",
		subreddit=db_subreddit.name
	)
	reddit.add_comment(comment)
	reddit.add_submission(RedditObject(id=submission_id, subreddit=db_subreddit.name, author=author_name))
	database.add_subscription(
		Subscription(
			subscriber=database.get_or_add_user(subscriber_name),
			author=database.get_or_add_user(author_name),
			subreddit=db_subreddit,
			recurring=True
		)
	)

	comments.process_comment(comment.get_pushshift_dict(), reddit, database)

	assert len(comment.children) == 0

	subscriptions = database.get_user_subscriptions_by_name(subscriber_name)
	assert len(subscriptions) == 1

	assert len(reddit.sent_messages) == 1
	assert "I have updated your subscription type" in reddit.sent_messages[0].body
	assert "next" in reddit.sent_messages[0].body
	assert db_subreddit.name in reddit.sent_messages[0].body
