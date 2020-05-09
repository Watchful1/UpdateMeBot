import discord_logging
from datetime import timedelta

log = discord_logging.get_logger(init=True)

import utils
from classes.submission import Submission
from classes.subscription import Subscription
from classes.comment import DbComment


def test_cleanup_comments(database, reddit):
	post_ids = [utils.random_id(), utils.random_id()]
	subreddit = database.get_or_add_subreddit("Subreddit1", enable_subreddit_if_new=True)
	submission1 = Submission(
		submission_id=post_ids[0],
		time_created=utils.datetime_now(),
		author=database.get_or_add_user("Author1"),
		subreddit=subreddit,
		permalink=""
	)
	database.add_submission(submission1)
	comment1 = DbComment(
		comment_id=utils.random_id(),
		submission=submission1,
		subscriber=database.get_or_add_user("Author2"),
		author=database.get_or_add_user("Author1"),
		subreddit=subreddit,
		recurring=False
	)
	comment1.time_created = utils.datetime_now() - timedelta(days=200)
	database.add_comment(comment1)
	submission2 = Submission(
		submission_id=post_ids[1],
		time_created=utils.datetime_now(),
		author=database.get_or_add_user("Author3"),
		subreddit=subreddit,
		permalink=""
	)
	database.add_submission(submission2)
	comment2 = DbComment(
		comment_id=utils.random_id(),
		submission=submission2,
		subscriber=database.get_or_add_user("Author4"),
		author=database.get_or_add_user("Author3"),
		subreddit=subreddit,
		recurring=False
	)
	database.add_comment(comment2)
	database.commit()

	database.clean()

	assert database.get_comment_by_thread(post_ids[0]) is None
	assert database.get_comment_by_thread(post_ids[1]) is not None


def test_cleanup_submissions(database, reddit):
	post_ids = [utils.random_id(), utils.random_id(), utils.random_id(), utils.random_id()]
	subreddit = database.get_or_add_subreddit("Subreddit1", enable_subreddit_if_new=True)
	submission1 = Submission(
		submission_id=post_ids[0],
		time_created=utils.datetime_now(),
		author=database.get_or_add_user("Author1"),
		subreddit=subreddit,
		permalink=""
	)
	submission1.time_created = utils.datetime_now() - timedelta(days=3)
	database.add_submission(submission1)
	submission2 = Submission(
		submission_id=post_ids[1],
		time_created=utils.datetime_now(),
		author=database.get_or_add_user("Author2"),
		subreddit=subreddit,
		permalink="",
		messages_sent=5
	)
	submission2.time_created = utils.datetime_now() - timedelta(days=5)
	database.add_submission(submission2)
	submission3 = Submission(
		submission_id=post_ids[2],
		time_created=utils.datetime_now(),
		author=database.get_or_add_user("Author3"),
		subreddit=subreddit,
		permalink=""
	)
	submission3.time_created = utils.datetime_now() - timedelta(days=4)
	database.add_submission(submission3)
	comment = DbComment(
		comment_id=utils.random_id(),
		submission=submission3,
		subscriber=database.get_or_add_user("Author5"),
		author=database.get_or_add_user("Author2"),
		subreddit=subreddit,
		recurring=False
	)
	database.add_comment(comment)
	submission4 = Submission(
		submission_id=post_ids[3],
		time_created=utils.datetime_now(),
		author=database.get_or_add_user("Author3"),
		subreddit=subreddit,
		permalink=""
	)
	database.add_submission(submission4)
	database.commit()

	database.clean()

	assert database.get_submission_by_id(post_ids[0]) is None
	assert database.get_submission_by_id(post_ids[1]) is not None
	assert database.get_submission_by_id(post_ids[2]) is not None
	assert database.get_submission_by_id(post_ids[3]) is not None


def test_cleanup_users(database, reddit):
	subreddit = database.get_or_add_subreddit("Subreddit1", enable_subreddit_if_new=True)
	submission1 = Submission(
		submission_id=utils.random_id(),
		time_created=utils.datetime_now(),
		author=database.get_or_add_user("Author1"),
		subreddit=subreddit,
		permalink=""
	)
	database.add_submission(submission1)
	submission2 = Submission(
		submission_id=utils.random_id(),
		time_created=utils.datetime_now(),
		author=database.get_or_add_user("Author6"),
		subreddit=subreddit,
		permalink=""
	)
	database.add_submission(submission2)
	previous_comment = DbComment(
		comment_id=utils.random_id(),
		submission=submission1,
		subscriber=database.get_or_add_user("Author3"),
		author=database.get_or_add_user("Author2"),
		subreddit=subreddit,
		recurring=False
	)
	database.add_comment(previous_comment)
	subscription = Subscription(
		subscriber=database.get_or_add_user("Author4"),
		author=database.get_or_add_user("Author5"),
		subreddit=subreddit,
		recurring=False
	)
	database.add_subscription(subscription)
	database.get_or_add_user("Author7")
	database.delete_submission(submission2)
	database.commit()

	database.clean()

	assert database.get_user("Author1") is not None
	assert database.get_user("Author2") is not None
	assert database.get_user("Author3") is not None
	assert database.get_user("Author4") is not None
	assert database.get_user("Author5") is not None
	assert database.get_user("Author6") is None
	assert database.get_user("Author7") is None
