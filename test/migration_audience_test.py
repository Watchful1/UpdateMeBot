import sqlite3
from datetime import datetime, timedelta

import migration_audience

NOW = datetime(2026, 11, 1, 12, 0, 0)


def notify_line(when, user, sub):
	return f"{when:%Y-%m-%d %H:%M:%S},123 - INFO: 1/1/1: Notifying u/{user} for u/author in r/{sub} : abc123\n"


def make_db(path, subscriptions, subreddits, failed=()):
	c = sqlite3.connect(path)
	c.execute("create table subreddits (id integer, name text, is_enabled boolean, is_blacklisted boolean)")
	c.execute("create table users (id integer, name text, first_failure datetime)")
	c.execute("create table subscriptions (subscriber_id integer, author_id integer, subreddit_id integer)")
	c.executemany("insert into subreddits values (?, ?, ?, ?)", subreddits)
	users = sorted({u for u, _ in subscriptions})
	c.executemany("insert into users values (?, ?, ?)", [(u, f"user{u}", NOW if u in failed else None) for u in users])
	c.executemany("insert into subscriptions values (?, 999, ?)", subscriptions)
	c.commit()
	c.close()


def test_users_are_people_notified_recently_from_affected_subreddits(tmp_path):
	# sub 1 used (10 people notified), sub 2 installed, sub 3 not enabled, sub 4 used profile
	subs = [(1, "Stories", 1, 0), (2, "Installed", 1, 0), (3, "Off", 0, 0), (4, "u_Writer", 1, 0)]
	subscriptions = [(u, 1) for u in range(1, 11)] + [(1, 2), (2, 3), (11, 4)] + [(u, 4) for u in range(12, 21)]
	make_db(tmp_path / "db.db", subscriptions, subs, failed={3})
	lines = [notify_line(NOW - timedelta(days=1), f"user{u}", "Stories") for u in range(1, 11)]
	lines += [notify_line(NOW, "user1", "Stories")]                        # user1: 2 sends
	lines += [notify_line(NOW - timedelta(days=200), "user2", "Stories")]  # outside the window
	lines += [notify_line(NOW, "user1", "Installed"), notify_line(NOW, "user2", "Off")]
	lines += [notify_line(NOW, f"user{u}", "u_Writer") for u in range(11, 21)]
	lines += [notify_line(NOW, "user5", "Stories"), "2026-11-01 12:00:01,1 - INFO: User blocked notification message: u/user5\n"]
	(tmp_path / "bot.log").write_text("".join(lines))

	audience = migration_audience.Audience(str(tmp_path / "db.db"), str(tmp_path / "bot.log*"), {"installed"})
	users = {name: (subs, n) for name, subs, n in audience.users()}

	assert users["user1"] == (["Stories"], 2)           # installed subreddit dropped from the list
	assert "user3" not in users                           # first_failure set
	assert users["user5"] == (["Stories"], 1)           # the blocked send doesn't count
	assert users["user11"] == (["u_Writer"], 1)         # profiles are messaged too
	assert audience.users()[0][0] == "user1"              # highest usage first


def test_modmail_subreddits_exclude_profiles_installed_and_unused(tmp_path):
	subs = [(1, "Stories", 1, 0), (2, "Installed", 1, 0), (3, "Quiet", 1, 0), (4, "u_Writer", 1, 0), (5, "Banned", 1, 1)]
	subscriptions = [(u, s) for s in (1, 2, 4, 5) for u in range(1, 11)] + [(u, 3) for u in range(1, 300)]
	make_db(tmp_path / "db.db", subscriptions, subs)
	lines = [notify_line(NOW, f"user{u}", sub) for sub in ("Stories", "Installed", "u_Writer", "Banned") for u in range(1, 11)]
	(tmp_path / "bot.log").write_text("".join(lines))

	audience = migration_audience.Audience(str(tmp_path / "db.db"), str(tmp_path / "bot.log*"), {"installed"})
	# Quiet is big enough to count as used, but sent nothing in the window: no one to tell about it
	assert audience.subreddits() == [("Stories", 10, 10)]
