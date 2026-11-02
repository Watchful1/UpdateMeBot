"""The one-off modmail to moderators of subreddits that use the bot but haven't installed.

Sent from u/Watchful1, not the bot, so moderators can reply; a reply is how a
subreddit opts out. Who gets one is in migration_audience.py: affected
subreddits that sent a notification in the last 90 days, profiles excluded.

  build   Writes one row per subreddit with its numbers, most notifications first.

            python scripts/migration_modmail.py build database.db "logs/bot.log*" modmail.csv

  send    Sends to every subreddit in the CSV not already sent, skipping any that
          installed since the build. Results are appended to the log as they
          happen; a rerun retries anything that didn't succeed.

            python scripts/migration_modmail.py send Watchful1 modmail.csv modmail-sent.csv --dry-run 3
            python scripts/migration_modmail.py send Watchful1 modmail.csv modmail-sent.csv --go --limit 10
            python scripts/migration_modmail.py send Watchful1 modmail.csv modmail-sent.csv --go

The install list comes from db-service, using updateme_api_key from the
praw.ini section named by --key-section (UpdateMeBot by default).

u/Watchful1 isn't whitelisted for bulk messaging like the bot is, so send goes
slowly (--delay, 30 seconds by default) and backs off when Reddit pushes back.
When Reddit asks it to wait, it waits that long plus a margin and retries; a
second rate limit in a row, a wait longer than 15 minutes, a failure before
any send in the run has gone through, or MAX_ERRORS_IN_A_ROW failures of any
kind stop the run. A rerun picks up from where it stopped.

Reddit takes "r/name" as the recipient for a subreddit's modmail. PRAW's
Subreddit.message() sends "#name", which Reddit now rejects as a user that
doesn't exist.
"""
import argparse
import csv
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import discord_logging

log = discord_logging.init_logging(filename="migration_modmail.log")

import praw_wrapper

import migration
import migration_audience
import migration_message
from migration_send import Stop, deliver

MAX_ERRORS_IN_A_ROW = 3


def api_key_for(section):
	key = praw_wrapper.reddit.get_config().get(section, "updateme_api_key", fallback=None)
	if key is None:
		log.error(f"No updateme_api_key in the [{section}] section of praw.ini")
		sys.exit(1)
	return key


def build(args):
	installed, _ = migration.fetch_status(api_key_for(args.key_section))
	rows = migration_audience.Audience(args.db, args.logs, installed).subreddits()
	with open(args.out, "w", newline="", encoding="utf-8") as fh:
		writer = csv.writer(fh)
		writer.writerow(["subreddit", "subscribers", "notifications"])
		writer.writerows(rows)
	short = sum(1 for _, _, n in rows if n < migration_message.static.MODMAIL_MIN_NOTIFICATIONS)
	log.info(f"Wrote {len(rows)} subreddits to {args.out} ({short} without the usage clause)")


def send(args):
	installed, _ = migration.fetch_status(api_key_for(args.key_section))
	with open(args.csv, newline="", encoding="utf-8") as fh:
		rows = [(r["subreddit"], int(r["subscribers"]), int(r["notifications"])) for r in csv.DictReader(fh)]
	done = set()
	if os.path.exists(args.log):
		with open(args.log, newline="", encoding="utf-8") as fh:
			done = {r["subreddit"].lower() for r in csv.DictReader(fh) if r["result"] in ("SUCCESS", "SKIPPED_INSTALLED")}
	todo = [r for r in rows if r[0].lower() not in done]
	log.info(f"{len(rows)} subreddits in {args.csv}, {len(done)} already done, {len(todo)} to go")

	if args.dry_run:
		for name, subscribers, notifications in todo[:args.dry_run]:
			subject, body = migration_message.render_modmail(name, subscribers, notifications)
			print(f"--- to r/{name}{' (installed, would skip)' if name.lower() in installed else ''}\n"
				f"Subject: {subject}\n\n{body}\n")
		return
	if not args.go:
		log.info("Nothing sent: pass --go to send for real, or --dry-run N to preview")
		return

	reddit = praw_wrapper.Reddit(args.user, user_agent="UpdateMeBot migration modmail").reddit
	new_log = not os.path.exists(args.log)
	sent, attempts, errors_in_a_row = 0, 0, 0
	with open(args.log, "a", newline="", encoding="utf-8") as log_file:
		writer = csv.writer(log_file)
		if new_log:
			writer.writerow(["subreddit", "result", "time"])
		try:
			for name, subscribers, notifications in todo:
				if args.limit and attempts >= args.limit:
					log.info(f"Reached --limit {args.limit}")
					break
				if name.lower() in installed:
					result = "SKIPPED_INSTALLED"
				else:
					if attempts:
						time.sleep(args.delay)
					attempts += 1
					subject, body = migration_message.render_modmail(name, subscribers, notifications)
					result = deliver(reddit, f"r/{name}", subject, body)
					if result == "SUCCESS":
						sent, errors_in_a_row = sent + 1, 0
						log.info(f"{sent}: r/{name}")
					else:
						errors_in_a_row += 1
						log.warning(f"r/{name}: {result}")
				writer.writerow([name, result, datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")])
				log_file.flush()
				# Failing before anything has gone through means the sending itself is broken
				if errors_in_a_row and not sent:
					raise Stop("the first send of this run failed")
				if errors_in_a_row >= MAX_ERRORS_IN_A_ROW:
					raise Stop(f"{errors_in_a_row} failures in a row, the account may be restricted")
		except Stop as err:
			log.error(f"Stopped: {err}")
	log.info(f"Sent {sent} this run")


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Migration modmail to subreddits that haven't installed")
	parser.add_argument("--key-section", default="UpdateMeBot", help="praw.ini section holding updateme_api_key")
	sub = parser.add_subparsers(dest="command", required=True)

	b = sub.add_parser("build", help="Write the list of subreddits to modmail")
	b.add_argument("db", help="Path to database.db or a backup of it")
	b.add_argument("logs", help="Glob for the bot's log files, quoted, e.g. \"logs/bot.log*\"")
	b.add_argument("out", help="CSV to write")

	s = sub.add_parser("send", help="Send to every subreddit in the list not already done")
	s.add_argument("user", help="praw.ini section for the sending account (Watchful1)")
	s.add_argument("csv", help="CSV from build")
	s.add_argument("log", help="Results log, appended to; reruns skip anything already sent")
	s.add_argument("--delay", type=float, default=30, help="Seconds to sleep between sends (default 30)")
	s.add_argument("--limit", type=int, default=None, help="Try at most this many subreddits, then stop")
	s.add_argument("--dry-run", type=int, default=0, metavar="N", help="Print N rendered messages, send nothing")
	s.add_argument("--go", action="store_true", help="Actually send. Without it, send only reports what's left")

	parsed = parser.parse_args()
	build(parsed) if parsed.command == "build" else send(parsed)
