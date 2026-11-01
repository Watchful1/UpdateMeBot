import discord_logging
from datetime import timedelta

log = discord_logging.get_logger(init=True)

import pytest

import migration
import notifications
import utils
from praw_wrapper import reddit_test
from notification_test import queue_message


@pytest.fixture(autouse=True)
def reset_migration_state():
	yield
	migration._installed = None
	migration._opted_out = set()
	migration._fetched_at = None


def send_one(database, reddit, subreddit_name):
	queue_message(database, "Subscriber1", "Author1", subreddit_name, reddit_test.random_id())
	notifications.send_queued_notifications(reddit, database)
	assert len(reddit.sent_messages) == 1
	return reddit.sent_messages[0].body


def test_no_notice_before_first_fetch(database, reddit):
	assert "developer platform" not in send_one(database, reddit, "Subreddit1")


def test_no_notice_for_installed_subreddit(database, reddit):
	migration.set_status(["subreddit1"], [], utils.datetime_now())
	assert "developer platform" not in send_one(database, reddit, "Subreddit1")


def test_notice_for_uninstalled_subreddit(database, reddit):
	migration.set_status(["othersub"], [], utils.datetime_now())
	body = send_one(database, reddit, "Subreddit1")
	assert "**Your notifications for r/Subreddit1 will stop soon.**" in body
	assert "only work in subreddits where the app is installed. [Learn more](" in body
	# Nothing that points the reader at moderators
	assert "moderator" not in body.lower()
	# Above the footer table, not inside or below it
	assert body.index("developer platform") < body.index("|[^(Info)]")


def test_profile_gets_profile_notice(database, reddit):
	migration.set_status([], [], utils.datetime_now())
	body = send_one(database, reddit, "u_Author1")
	assert "**Your notifications for u/Author1's profile posts will stop soon.**" in body
	assert "can't be installed on user profiles" in body
	assert "can install it" not in body


def test_stale_status_adds_no_notice(database, reddit):
	migration.set_status([], [], utils.datetime_now() - migration.STALE_AFTER - timedelta(minutes=1))
	assert "developer platform" not in send_one(database, reddit, "Subreddit1")


def test_refresh_failure_keeps_last_status(monkeypatch):
	migration.set_status(["subreddit1"], [], utils.datetime_now())
	monkeypatch.setattr(migration, "_api_key", "key")
	monkeypatch.setattr(migration, "_last_attempt", None)

	def boom(*args, **kwargs):
		raise migration.requests.exceptions.ConnectionError("down")
	monkeypatch.setattr(migration.requests, "get", boom)

	migration.refresh()
	assert migration.get_notice("Subreddit1") is None
	assert migration.get_notice("Othersub") is not None
