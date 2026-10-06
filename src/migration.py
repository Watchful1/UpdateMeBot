import discord_logging
import requests
import traceback
from datetime import timedelta

log = discord_logging.get_logger()

import counters
import static
import utils


# Which subreddits have installed the new Devvit app, and which have opted out
# of being asked, polled from db-service's /migration-status. Notifications from
# a subreddit that hasn't installed get a notice appended telling the subscriber
# their notifications there will stop at the migration.
#
# Fails closed: until the first successful fetch, or once the last one is older
# than STALE_AFTER, no notice is added at all. A missing warning costs nothing;
# a false "this subreddit hasn't installed" in r/nosleep would be wrong in front
# of thousands of people.

POLL_EVERY = timedelta(minutes=10)
STALE_AFTER = timedelta(hours=6)

_api_key = None
_installed = None
_opted_out = set()
_fetched_at = None
_last_attempt = None


def init(api_key):
	global _api_key
	_api_key = api_key
	if api_key is None:
		log.info("No updateme_api_key in praw.ini, migration notices disabled")


def set_status(installed, opted_out, fetched_at):
	global _installed, _opted_out, _fetched_at
	_installed = set(name.lower() for name in installed)
	_opted_out = set(name.lower() for name in opted_out)
	_fetched_at = fetched_at
	counters.objects.labels(type="migration_installed").set(len(_installed))
	counters.objects.labels(type="migration_opted_out").set(len(_opted_out))


def fetch_status(api_key):
	"""(installed, opted_out) as lowercase name sets. Raises on any failure."""
	response = requests.get(
		static.MIGRATION_STATUS_URL,
		headers={'Authorization': f"Bearer {api_key}", 'User-Agent': static.USER_AGENT},
		timeout=10)
	response.raise_for_status()
	data = response.json()
	return set(n.lower() for n in data['installed']), set(n.lower() for n in data['optedOut'])


def refresh():
	global _last_attempt
	if _api_key is None or not utils.time_offset(_last_attempt, seconds=int(POLL_EVERY.total_seconds())):
		return
	_last_attempt = utils.datetime_now()
	try:
		installed, opted_out = fetch_status(_api_key)
		set_status(installed, opted_out, utils.datetime_now())
		log.debug(f"Migration status: {len(_installed)} installed, {len(_opted_out)} opted out")
	except Exception as err:
		utils.process_error("Error fetching migration status, keeping the last one", err, traceback.format_exc())


def get_notice(subreddit_name):
	if _installed is None or _fetched_at is None or _fetched_at < utils.datetime_now() - STALE_AFTER:
		return None
	name = subreddit_name.lower()
	if name in _installed:
		return None

	if name.startswith("u_"):
		return static.MIGRATION_NOTICE_PROFILE.format(author=subreddit_name[2:], link=static.MIGRATION_POST)
	if name in _opted_out:
		return static.MIGRATION_NOTICE_OPTED_OUT.format(subreddit=subreddit_name, link=static.MIGRATION_POST)
	return static.MIGRATION_NOTICE.format(subreddit=subreddit_name, link=static.MIGRATION_POST)
