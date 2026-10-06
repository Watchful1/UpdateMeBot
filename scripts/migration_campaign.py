"""The one-off bulk message telling subscribers their notifications will stop.

Two steps, both run on the bot server:

  build   Reads the database and the live install / opt-out lists, writes one
          row per user to message. Safe against the live database.db (opened
          read-only) or a backup.

            python scripts/migration_campaign.py build UpdateMeBot database.db campaign.csv

  send    Works through that CSV as the bot account. Every result is appended
          to the log as it happens, so it can be stopped with ctrl-c and rerun:
          anyone already done is skipped, transient failures are retried.

            python scripts/migration_campaign.py send UpdateMeBot campaign.csv sent.csv --dry-run 5
            python scripts/migration_campaign.py send UpdateMeBot campaign.csv sent.csv --go --limit 1000
            python scripts/migration_campaign.py send UpdateMeBot campaign.csv sent.csv --go

          Without --go or --dry-run, send only reports how many are left.

Who gets one (the decisions behind these are in the devvit-apps repo,
docs/apps/updateme-migration-state.md and scripts/outreach/):
  - One message per user, listing every affected subreddit, most active first.
  - Affected: enabled, not blacklisted, not a u_ profile, and not installed.
    Profiles are left out; their notifications carry their own notice.
  - Only users with at least one affected subreddit that sent a notification in
    the last 90 days. Users only in dormant subreddits would never notice.
  - Accounts with first_failure set are skipped: deleted, suspended, or
    blocking the bot.

Installs keep happening during a ~1.5 day send, so send re-fetches the install
list every 10 minutes and drops newly installed subreddits from each message;
a user left with none is skipped.

The bot itself sends notifications with the same account. --prefix picks a
separate OAuth app from praw.ini ({prefix}client_id etc.) so the two don't
share one rate limit.
"""
import argparse
import csv
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import discord_logging

log = discord_logging.init_logging(backup_count=20)

import praw_wrapper
from praw_wrapper.reddit import ReturnType

import migration
import migration_message

REFRESH_EVERY = timedelta(minutes=10)
# Retried on a rerun. Anything else is final: sent, or never deliverable.
TRANSIENT = {ReturnType.SERVER_ERROR, ReturnType.NOTHING_RETURNED, ReturnType.SOMETHING_IS_BROKEN, ReturnType.RATELIMIT}


def api_key_for(user):
	key = praw_wrapper.reddit.get_config().get(user, "updateme_api_key", fallback=None)
	if key is None:
		log.error(f"No updateme_api_key in the [{user}] section of praw.ini")
		sys.exit(1)
	return key


def build(args):
	installed, opted_out = migration.fetch_status(api_key_for(args.user))
	log.info(f"{len(installed)} installed, {len(opted_out)} opted out")

	c = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
	c.execute("pragma cache_size = -400000")

	affected = {
		sid: name for sid, name in c.execute(
			"select id, name from subreddits where is_enabled = 1 and is_blacklisted = 0")
		if not name.lower().startswith("u_") and name.lower() not in installed}
	sends = dict(c.execute(
		"select subreddit_id, sum(messages_sent) from submissions "
		"where time_created > datetime('now', '-90 days') group by subreddit_id"))

	placeholders = ",".join("?" * len(affected))
	by_user = {}
	for uid, sid in c.execute(
			f"select distinct subscriber_id, subreddit_id from subscriptions where subreddit_id in ({placeholders})",
			list(affected)):
		by_user.setdefault(uid, []).append(sid)

	names = dict(c.execute("select id, name from users"))
	failed = set(r[0] for r in c.execute("select id from users where first_failure is not null"))

	rows, skipped_failed, skipped_dormant = [], 0, 0
	for uid, sids in by_user.items():
		if uid in failed:
			skipped_failed += 1
			continue
		if not any(sends.get(sid, 0) > 0 for sid in sids):
			skipped_dormant += 1
			continue
		if uid not in names:
			continue
		sids.sort(key=lambda sid: (-sends.get(sid, 0), affected[sid].lower()))
		rows.append((names[uid], ";".join(affected[sid] for sid in sids)))

	rows.sort(key=lambda r: r[0].lower())
	with open(args.out, "w", newline="", encoding="utf-8") as fh:
		writer = csv.writer(fh)
		writer.writerow(["username", "subreddits"])
		writer.writerows(rows)

	counts = {}
	for _, subs in rows:
		n = subs.count(";") + 1
		bucket = "1" if n == 1 else "2-3" if n <= 3 else "4-10" if n <= 10 else "11+"
		counts[bucket] = counts.get(bucket, 0) + 1
	log.info(f"Wrote {len(rows):,} users to {args.out}")
	log.info(f"  by affected subreddits: {counts}")
	log.info(f"  skipped {skipped_failed:,} unreachable accounts, {skipped_dormant:,} only in dormant subreddits")


def load_done(log_path):
	done = set()
	if os.path.exists(log_path):
		with open(log_path, newline="", encoding="utf-8") as fh:
			for row in csv.DictReader(fh):
				if row["result"] not in {r.name for r in TRANSIENT}:
					done.add(row["username"].lower())
	return done


def send(args):
	api_key = api_key_for(args.user)
	with open(args.csv, newline="", encoding="utf-8") as fh:
		users = [(r["username"], r["subreddits"].split(";")) for r in csv.DictReader(fh)]
	done = load_done(args.log)
	todo = [(u, subs) for u, subs in users if u.lower() not in done]
	log.info(f"{len(users):,} users in {args.csv}, {len(done):,} already done, {len(todo):,} to go")

	if args.dry_run:
		installed, opted_out = migration.fetch_status(api_key)
		for username, subs in todo[:args.dry_run]:
			remaining = [s for s in subs if s.lower() not in installed]
			if not remaining:
				print(f"--- u/{username}: every subreddit has installed, would skip\n")
				continue
			subject, body = migration_message.render(remaining, opted_out)
			print(f"--- to u/{username}\nSubject: {subject}\n\n{body}\n")
		return
	if not args.go:
		log.info("Nothing sent: pass --go to send for real, or --dry-run N to preview")
		return

	reddit = praw_wrapper.Reddit(args.user, prefix=args.prefix, user_agent="UpdateMeBot migration notice")
	new_log = not os.path.exists(args.log)
	log_file = open(args.log, "a", newline="", encoding="utf-8")
	log_writer = csv.writer(log_file)
	if new_log:
		log_writer.writerow(["username", "result", "subreddits", "time"])

	installed, opted_out, fetched_at = None, None, None
	started, sent = time.perf_counter(), 0
	limit = args.limit or len(todo)
	try:
		for username, subs in todo[:limit]:
			if fetched_at is None or datetime.utcnow() - fetched_at > REFRESH_EVERY:
				try:
					installed, opted_out = migration.fetch_status(api_key)
					fetched_at = datetime.utcnow()
				except Exception as err:
					if installed is None:
						raise
					log.warning(f"Couldn't refresh the install list, using the last one: {err}")
					fetched_at = datetime.utcnow()

			remaining = [s for s in subs if s.lower() not in installed]
			if not remaining:
				result = "SKIPPED_ALL_INSTALLED"
			else:
				subject, body = migration_message.render(remaining, opted_out)
				result = reddit.send_message(username, subject, body, retry_seconds=300).name
				sent += 1
			log_writer.writerow([username, result, ";".join(remaining), datetime.utcnow().isoformat(timespec="seconds")])
			log_file.flush()
			if result not in ("SUCCESS", "SKIPPED_ALL_INSTALLED"):
				log.info(f"u/{username}: {result}")

			if sent and sent % 100 == 0:
				per_minute = sent / ((time.perf_counter() - started) / 60)
				log.info(f"{sent:,} sent, {per_minute:.0f}/min, about {(len(todo) - sent) / per_minute / 60:.1f} hours left")
			if args.delay:
				time.sleep(args.delay)
	finally:
		log_file.close()
		log.info(f"Stopped after sending {sent:,}")


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Bulk migration message to UpdateMeBot subscribers")
	sub = parser.add_subparsers(dest="command", required=True)

	b = sub.add_parser("build", help="Write the list of users to message")
	b.add_argument("user", help="praw.ini section holding updateme_api_key")
	b.add_argument("db", help="Path to database.db or a backup of it")
	b.add_argument("out", help="CSV to write")

	s = sub.add_parser("send", help="Send to everyone in the list not already done")
	s.add_argument("user", help="praw.ini section for the bot account")
	s.add_argument("csv", help="CSV from build")
	s.add_argument("log", help="Results log, appended to; reruns skip anyone done in it")
	s.add_argument("--prefix", default=None, help="praw.ini key prefix for a separate OAuth app")
	s.add_argument("--limit", type=int, default=None, help="Send at most this many, then stop")
	s.add_argument("--delay", type=float, default=0, help="Seconds to sleep between sends")
	s.add_argument("--dry-run", type=int, default=0, metavar="N", help="Print N rendered messages, send nothing")
	s.add_argument("--go", action="store_true", help="Actually send. Without it, send only reports what's left")

	parsed = parser.parse_args()
	build(parsed) if parsed.command == "build" else send(parsed)
