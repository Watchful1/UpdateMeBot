import collections
import glob
import re
import sqlite3
from datetime import timedelta, datetime

import discord_logging

log = discord_logging.get_logger()


# Who the migration outreach goes to, worked out from the database and the bot's
# own logs. The logs are the only record of who actually got a notification:
# notification rows are deleted once sent.
#
# A subreddit is affected if it's enabled in this bot, not blacklisted, hasn't
# installed the Devvit app, and is used: more than BIG_SUBREDDIT subscribers, or
# at least MIN_NOTIFIED people notified from it in the window. These are the
# defaults on the "UpdateMeBot Reach" page the admins approved the plan from.

WINDOW_DAYS = 90
BIG_SUBREDDIT = 200
MIN_NOTIFIED = 10

NOTIFY_RE = re.compile(
	r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d),\d+ - INFO: [\d/]+: Notifying u/(\S+) for u/\S+ in r/(\S+) : \S+")
# Failure lines follow straight after the Notifying line they belong to
FAIL_RE = re.compile(
	r"(?:User doesn't exist|User blocked notification message|User moderator filter blocked notification message|"
	r"Failure sending notification message to|something was too long): u/(\S+)")


def read_sends(log_glob):
	"""[(time, username lower, subreddit lower)] for every successful notification in the logs."""
	sends = []
	paths = glob.glob(log_glob)
	if not paths:
		raise FileNotFoundError(f"No log files match {log_glob}")
	for path in paths:
		last = None
		with open(path, encoding="utf-8", errors="replace") as fh:
			for line in fh:
				match = NOTIFY_RE.match(line)
				if match:
					last = [datetime.strptime(match[1], "%Y-%m-%d %H:%M:%S"), match[2].lower(), match[3].lower(), True]
					sends.append(last)
					continue
				failed = FAIL_RE.search(line)
				if failed and last is not None and failed[1].lower() == last[1]:
					last[3] = False
	return [(ts, user, sub) for ts, user, sub, ok in sends if ok]


class Audience:
	def __init__(self, db_path, log_glob, installed):
		sends = read_sends(log_glob)
		self.log_end = max(ts for ts, _, _ in sends)
		cutoff = self.log_end - timedelta(days=WINDOW_DAYS)
		log.info(f"Logs end {self.log_end:%Y-%m-%d %H:%M}, counting notifications since {cutoff:%Y-%m-%d}")

		c = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
		c.execute("pragma cache_size = -400000")
		subreddits = {sid: (name, enabled, blacklisted) for sid, name, enabled, blacklisted in c.execute(
			"select id, name, is_enabled, is_blacklisted from subreddits")}
		self.names = dict(c.execute("select id, name from users"))
		self.failed = set(r[0] for r in c.execute("select id from users where first_failure is not null"))
		self.subscribed = collections.defaultdict(set)
		for uid, sid in c.execute("select distinct subscriber_id, subreddit_id from subscriptions"):
			self.subscribed[uid].add(sid)
		self.subscribers = collections.Counter(sid for sids in self.subscribed.values() for sid in sids)

		uid_by_name = {name.lower(): uid for uid, name in self.names.items()}
		sid_by_name = {name.lower(): sid for sid, (name, _, _) in subreddits.items()}
		self.notifications = collections.Counter()           # sid -> successful sends in the window
		notified = collections.defaultdict(set)              # sid -> users notified in the window
		self.user_counts = collections.defaultdict(collections.Counter)   # uid -> sid -> sends
		for ts, user, sub in sends:
			if ts < cutoff or sub not in sid_by_name or user not in uid_by_name:
				continue
			uid, sid = uid_by_name[user], sid_by_name[sub]
			self.notifications[sid] += 1
			notified[sid].add(uid)
			self.user_counts[uid][sid] += 1

		self.subreddit_names = {sid: name for sid, (name, _, _) in subreddits.items()}
		self.affected = {
			sid for sid, (name, enabled, blacklisted) in subreddits.items()
			if enabled and not blacklisted and name.lower() not in installed
			and (self.subscribers[sid] > BIG_SUBREDDIT or len(notified[sid]) >= MIN_NOTIFIED)}

	def users(self):
		"""[(username, [subreddit names, most notifications first], notifications)], highest usage first.

		A user is in if they were notified in the window from an affected subreddit
		they're still subscribed in. One-time subscriptions that already fired are
		gone, so those people lose nothing."""
		rows = []
		for uid, counts in self.user_counts.items():
			if uid in self.failed or uid not in self.names:
				continue
			subs = [sid for sid in counts if sid in self.affected and sid in self.subscribed[uid]]
			if not subs:
				continue
			subs.sort(key=lambda sid: (-counts[sid], self.subreddit_names[sid].lower()))
			rows.append((self.names[uid], [self.subreddit_names[sid] for sid in subs], sum(counts[sid] for sid in subs)))
		rows.sort(key=lambda r: (-r[2], r[0].lower()))
		return rows

	def subreddits(self):
		"""[(subreddit name, subscribers, notifications)] for the modmail, most notifications first.

		Affected subreddits that sent anything in the window. Profiles are left
		out: they can't install apps, so there's no one to ask."""
		rows = [
			(self.subreddit_names[sid], self.subscribers[sid], self.notifications[sid])
			for sid in self.affected
			if self.notifications[sid] > 0 and not self.subreddit_names[sid].lower().startswith("u_")]
		rows.sort(key=lambda r: (-r[2], r[0].lower()))
		return rows
