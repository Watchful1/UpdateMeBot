from datetime import datetime
import discord_logging
import re
import urllib.parse
import prawcore
from datetime import timedelta


log = discord_logging.get_logger()


import counters
import static


def process_error(message, exception, traceback):
	is_transient = isinstance(exception, prawcore.exceptions.ServerError)
	log.warning(f"{message}: {exception}")
	if is_transient:
		log.info(traceback)
		counters.errors.labels(type='api').inc()
	else:
		log.warning(traceback)
		counters.errors.labels(type='other').inc()

	return is_transient


def extract_tag_from_title(title):
	if title is None:
		return None
	match = re.search(r"(?:\[)(.+?)(?:\])", title)
	if match:
		tag = match[1]
	else:
		match = re.search(r"^(.+?)(?:[-:])", title)
		if match:
			tag = match[1]
		else:
			return None

	return re.sub(r"[^\w\d ]", "", tag.strip())


def check_update_disabled_subreddit(database, subreddit):
	log.debug(f"Checking if disabled subreddit has passed threshold r/{subreddit.name}")
	count_subscriptions = database.get_count_subscriptions_for_subreddit(subreddit)
	if count_subscriptions >= subreddit.notice_threshold:
		bldr = str_bldr()
		bldr.append("r/")
		bldr.append(subreddit.name)
		bldr.append(" has passed the notice threshold with ")
		bldr.append(str(count_subscriptions))
		bldr.append(" requests. It has ")
		bldr.append(str(subreddit.posts_per_hour))
		bldr.append(" posts per hour: <")
		bldr.append(
			build_message_link(
				static.ACCOUNT_NAME, 'Add sub', f'AddSubreddit r/{subreddit.name} subscribe'
			)
		)
		bldr.append(">")
		log.warning(''.join(bldr))
		subreddit.notice_threshold = subreddit.notice_threshold * 2


def datetime_now():
	return datetime.utcnow().replace(microsecond=0)


def date_now():
	return datetime.utcnow().date()


def get_datetime_string(date_time, format_string="%Y-%m-%d %H:%M:%S"):
	if date_time is None:
		return ""
	return date_time.strftime(format_string)


def parse_datetime_string(date_time_string, format_string="%Y-%m-%d %H:%M:%S"):
	if date_time_string is None or date_time_string == "None" or date_time_string == "":
		return None
	date_time = datetime.strptime(date_time_string, format_string)
	return date_time


def html_encode(message):
	return urllib.parse.quote(message, safe='')


def build_message_link(recipient, subject, content=None):
	base = "https://www.reddit.com/message/compose/?"
	bldr = str_bldr()
	bldr.append(f"to={recipient}")
	bldr.append(f"subject={html_encode(subject)}")
	if content is not None:
		bldr.append(f"message={html_encode(content)}")

	return base + '&'.join(bldr)


def requests_available(requests_pending):
	if requests_pending == 0:
		return 0
	elif requests_pending < 200:
		return 30
	else:
		return min(1000, int(requests_pending / 5))


def time_offset(date_time, hours=0, minutes=0, seconds=0):
	if date_time is None:
		return True
	return date_time < datetime_now() - timedelta(hours=hours, minutes=minutes, seconds=seconds)


def get_footer(bldr=None):
	if bldr is None:
		bldr = []
	bldr.append("\n\n")
	bldr.append("*****")
	bldr.append("\n\n")

	bldr.append("|[^(Info)](")
	bldr.append(static.INFO_POST)
	bldr.append(")|[^(Request Update)](")
	bldr.append(build_message_link(
		static.ACCOUNT_NAME,
		"Update",
		"SubscribeMe! u/username r/subreddit"
	))
	bldr.append(")")
	bldr.append("|[^(Your Updates)](")
	bldr.append(build_message_link(
		static.ACCOUNT_NAME,
		"List Of Updates",
		"MyUpdates"
	))
	bldr.append(")")
	bldr.append("|[^(Feedback)](")
	bldr.append(build_message_link(
		static.OWNER,
		"UpdateMeBot Feedback"
	))
	bldr.append(")")
	bldr.append("|\n|-|-|-|-|")

	return bldr


def str_bldr():
	return []
