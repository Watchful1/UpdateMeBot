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
            python scripts/migration_modmail.py send Watchful1 modmail.csv modmail-sent.csv --go

The install list comes from db-service, using updateme_api_key from the
praw.ini section named by --key-section (UpdateMeBot by default).
"""
import argparse
import csv
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import discord_logging

log = discord_logging.init_logging(backup_count=20)

import praw_wrapper

import migration
import migration_audience
import migration_message


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
	with open(args.log, "a", newline="", encoding="utf-8") as log_file:
		writer = csv.writer(log_file)
		if new_log:
			writer.writerow(["subreddit", "result", "time"])
		for name, subscribers, notifications in todo:
			if name.lower() in installed:
				result = "SKIPPED_INSTALLED"
			else:
				subject, body = migration_message.render_modmail(name, subscribers, notifications)
				try:
					# Keyword arguments: PRAW 8 made subject and message keyword-only
					reddit.subreddit(name).message(subject=subject, message=body)
					result = "SUCCESS"
				except Exception as err:
					result = f"ERROR {type(err).__name__}: {err}"
					log.warning(f"r/{name}: {result}")
				time.sleep(args.delay)
			writer.writerow([name, result, datetime.utcnow().isoformat(timespec="seconds")])
			log_file.flush()
	log.info("Done")


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
	s.add_argument("--delay", type=float, default=3, help="Seconds to sleep between sends")
	s.add_argument("--dry-run", type=int, default=0, metavar="N", help="Print N rendered messages, send nothing")
	s.add_argument("--go", action="store_true", help="Actually send. Without it, send only reports what's left")

	parsed = parser.parse_args()
	build(parsed) if parsed.command == "build" else send(parsed)
