#!/usr/bin/python3

import logging.handlers
import sys
import signal
import time
import traceback
import discord_logging
import praw_wrapper
import argparse

log = discord_logging.init_logging(
	backup_count=20
)


import counters
from database import Database
import static
import messages
import comments
import subreddits
import notifications
import utils
import stats


database = None
ingest_database = None


def signal_handler(signal, frame):
	log.info("Handling interrupt")
	database.close()
	ingest_database.close()
	discord_logging.flush_discord()
	sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Reddit UpdateMe bot")
	parser.add_argument("user", help="The reddit user account to use")
	parser.add_argument("--once", help="Only run the loop once", action='store_const', const=True, default=False)
	parser.add_argument("--debug_db", help="Use the debug database", action='store_const', const=True, default=False)
	parser.add_argument(
		"--no_post", help="Print out reddit actions instead of posting to reddit", action='store_const', const=True,
		default=False)
	parser.add_argument(
		"--no_backup", help="Don't backup the database", action='store_const', const=True, default=False)
	parser.add_argument(
		"--reset_comment", help="Reset the last comment read timestamp", action='store_const', const=True,
		default=False)
	parser.add_argument("--debug", help="Set the log level to debug", action='store_const', const=True, default=False)
	parser.add_argument("--ingest_db", help="The location of the ingest database file", default=None)
	parser.add_argument(
		"--no_profile", help="Don't run the profile process", action='store_const', const=True, default=False)
	args = parser.parse_args()

	counters.init(8000)
	counters.errors.labels(type="startup").inc()

	if args.debug:
		discord_logging.set_level(logging.DEBUG)

	discord_logging.init_discord_logging(args.user, logging.WARNING, 1)
	static.ACCOUNT_NAME = args.user
	reddit = praw_wrapper.Reddit(args.user, args.no_post, user_agent=static.USER_AGENT)
	static.ACCOUNT_NAME = reddit.username
	database = Database(debug=args.debug_db)

	ingest_database = None
	if args.ingest_db:
		ingest_database = praw_wrapper.IngestDatabase(location=args.ingest_db)
		ingest_database.set_default_client("updateme")
		ingest_database.register_search(search_term="updateme")
		ingest_database.register_search(search_term="subscribeme")
		ingest_database.register_search(search_term="subscribeall")

	if args.reset_comment:
		log.info("Resetting comment processed timestamp")
		database.save_datetime("comment_timestamp", utils.datetime_now())

	last_backup = None
	last_comments = None
	while True:
		startTime = time.perf_counter()
		log.debug("Starting run")

		actions = 0
		errors = 0

		counters.objects.labels(type="subscriptions").set(database.get_count_all_subscriptions())
		counters.objects.labels(type="comments").set(database.get_count_all_comments())
		counters.objects.labels(type="submissions").set(database.get_count_all_submissions())
		counters.objects.labels(type="stats").set(database.get_count_all_stats())
		counters.objects.labels(type="users").set(database.get_count_all_users())
		counters.objects.labels(type="subreddits").set(database.get_count_all_subreddits())

		try:
			actions += messages.process_messages(reddit, database)
		except Exception as err:
			utils.process_error(f"Error processing messages", err, traceback.format_exc())
			errors += 1

		try:
			subreddits.scan_subreddits(reddit, database)
		except Exception as err:
			utils.process_error(f"Error scanning subreddits", err, traceback.format_exc())
			errors += 1

		try:
			actions += comments.process_comments(reddit, database, ingest_database)
		except Exception as err:
			utils.process_error(f"Error processing comments", err, traceback.format_exc())
			errors += 1

		try:
			actions += notifications.send_queued_notifications(reddit, database)
		except Exception as err:
			utils.process_error(f"Error sending notifications", err, traceback.format_exc())
			errors += 1

		if not args.no_profile:
			try:
				subreddits.profile_subreddits(reddit, database)
			except Exception as err:
				utils.process_error(f"Error profiling subreddits", err, traceback.format_exc())
				errors += 1

		try:
			subreddits.unmute_subreddits(database)
		except Exception as err:
			utils.process_error(f"Error profiling subreddits", err, traceback.format_exc())
			errors += 1

		try:
			actions += subreddits.recheck_submissions(reddit, database)
		except Exception as err:
			utils.process_error(f"Error rechecking submissions", err, traceback.format_exc())
			errors += 1

		if utils.time_offset(last_comments, minutes=30):
			try:
				actions += comments.update_comments(reddit, database)
				last_comments = utils.datetime_now()
			except Exception as err:
				utils.process_error(f"Error updating comments", err, traceback.format_exc())
				errors += 1

		# latest_stats = database.get_datetime("stats_day", is_date=True)
		# current_day = utils.date_now()
		# if latest_stats is None:
		# 	database.save_datetime("stats_day", current_day)
		# elif latest_stats != current_day:
		# 	log.info(f"Saving stats for day {current_day.strftime('%Y-%m-%d')}")
		# 	stats.save_stats_for_day(database, latest_stats)
		# 	database.save_datetime("stats_day", current_day)

		if not args.no_backup and utils.time_offset(last_backup, hours=8):
			try:
				database.backup()
				last_backup = utils.datetime_now()

				database.clean()
			except Exception as err:
				utils.process_error(f"Error backing up database", err, traceback.format_exc())
				errors += 1

		run_time = time.perf_counter() - startTime
		counters.run_time.observe(round(run_time, 2))
		log.debug(f"Run complete after: {int(run_time)}")

		discord_logging.flush_discord()
		database.commit()

		if args.once:
			break

		sleep_time = max(30 - actions, 0) + (30 * errors)
		counters.sleep_time.observe(sleep_time)
		log.debug(f"Sleeping {sleep_time}")

		time.sleep(sleep_time)
