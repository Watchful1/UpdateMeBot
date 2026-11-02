import discord_logging
import re
import time

log = discord_logging.get_logger()

import praw.exceptions
import prawcore.exceptions


# Sending for the one-off migration scripts (scripts/migration_campaign.py and
# scripts/migration_modmail.py). They call PRAW directly rather than going
# through praw_wrapper.send_message, which passes subject and body positionally
# and reads err.error_type: PRAW 8 rejects the first and dropped the second.

MAX_WAIT = 15 * 60
RATELIMIT_WAIT = re.compile(r"(\d+) (millisecond|second|minute)", re.IGNORECASE)
UNIT_SECONDS = {"millisecond": 0.001, "second": 1, "minute": 60}


class Stop(Exception):
	pass


def ratelimit_wait(err):
	"""Seconds Reddit asked to wait, or None if err isn't a rate limit."""
	if not isinstance(err, praw.exceptions.RedditAPIException):
		return None
	for item in err.items:
		if item.error_type == "RATELIMIT":
			match = RATELIMIT_WAIT.search(item.message or "")
			# No duration in the message: treat it as too long to wait out
			if match is None:
				return MAX_WAIT + 1
			return int(match.group(1)) * UNIT_SECONDS[match.group(2).lower()]
	return None


def deliver(reddit, recipient, subject, body):
	"""Sends one message. recipient is a username, or "r/name" for a subreddit's modmail.

	Returns "SUCCESS", Reddit's error type (e.g. "USER_DOESNT_EXIST"), or "ERROR ..."
	for anything else. Waits out one rate limit; raises Stop on a second, or on a
	wait longer than MAX_WAIT.
	"""
	for attempt in range(2):
		try:
			reddit.redditor(recipient).message(subject=subject, message=body)
			return "SUCCESS"
		except Exception as err:
			wait = ratelimit_wait(err)
			if wait is None:
				if isinstance(err, praw.exceptions.RedditAPIException) and err.items:
					return err.items[0].error_type
				if isinstance(err, prawcore.exceptions.Forbidden):
					return "FORBIDDEN"
				if isinstance(err, prawcore.exceptions.ServerError):
					return "SERVER_ERROR"
				return f"ERROR {type(err).__name__}: {err}"
			if attempt > 0 or wait > MAX_WAIT:
				raise Stop(f"Rate limited sending to {recipient}: {err}")
			log.warning(f"Rate limited, waiting {wait + 60:.0f} seconds: {err}")
			time.sleep(wait + 60)
