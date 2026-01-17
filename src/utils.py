from datetime import datetime
import discord_logging
import re
import urllib.parse
import prawcore
import requests
import urllib3
from datetime import timedelta


log = discord_logging.get_logger()


import counters
import static


def process_error(message, exception, traceback):
	is_transient = \
		isinstance(exception, prawcore.exceptions.ServerError) or \
		isinstance(exception, prawcore.exceptions.ResponseException) or \
		isinstance(exception, prawcore.exceptions.RequestException) or \
		isinstance(exception, requests.exceptions.Timeout) or \
		isinstance(exception, requests.exceptions.ReadTimeout) or \
		isinstance(exception, requests.exceptions.RequestException) or \
		isinstance(exception, urllib3.exceptions.ReadTimeoutError)
	log.warning(f"{message}: {type(exception).__name__} : {exception}")
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
		bldr.append(" posts per hour: [Subscribe](<")
		bldr.append(
			build_message_link(
				static.ACCOUNT_NAME, 'Add sub', f'AddSubreddit r/{subreddit.name} subscribe'
			)
		)
		bldr.append(">) : [Update](<")
		bldr.append(
			build_message_link(
				static.ACCOUNT_NAME, 'Add sub', f'AddSubreddit r/{subreddit.name} update'
			)
		)
		bldr.append(">) : [Blacklist](<")
		bldr.append(
			build_message_link(
				static.ACCOUNT_NAME, 'Add sub', f'SubredditBlacklist r/{subreddit.name}'
			)
		)
		bldr.append(">)")
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
	try:
		date_time = datetime.strptime(date_time_string, format_string)
	except ValueError:
		return None
	return date_time


def html_encode(message):
	return urllib.parse.quote(message, safe='')


def build_message_link(recipient, subject, content=None, label=None):
	base = "https://www.reddit.com/message/compose/?"
	bldr = str_bldr()
	bldr.append(f"to={recipient}")
	bldr.append(f"subject={html_encode(subject)}")
	if content is not None:
		bldr.append(f"message={html_encode(content)}")

	url = base + '&'.join(bldr)
	if label is not None:
		return f"[{label}]({url})"
	else:
		return url


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
	columns = 0
	if bldr is None:
		bldr = []
	bldr.append("\n\n")
	bldr.append("*****")
	bldr.append("\n\n")

	bldr.append("|[^(Info)](")
	bldr.append(static.INFO_POST)
	columns += 1
	bldr.append(")|[^(Request Update)](")
	bldr.append(build_message_link(
		static.ACCOUNT_NAME,
		"Update",
		"SubscribeMe! u/username r/subreddit"
	))
	bldr.append(")")
	columns += 1
	bldr.append("|[^(Your Updates)](")
	bldr.append(build_message_link(
		static.ACCOUNT_NAME,
		"List Of Updates",
		"MyUpdates"
	))
	bldr.append(")")
	columns += 1
	bldr.append("|[^(Feedback)](")
	bldr.append(build_message_link(
		static.OWNER,
		"UpdateMeBot Feedback"
	))
	bldr.append(")")
	columns += 1

	# # new post section
	# bldr.append("|[*^(New!)*](")
	# bldr.append(static.NEW_POST)
	# bldr.append(")")
	# columns += 1

	bldr.append("|\n|")
	bldr.append("-|" * columns)

	return bldr


def str_bldr():
	return []


def bldr_length(bldr):
	length = 0
	for item in bldr:
		length += len(item.encode('utf-8'))
	return length


def reddit_link(subreddit, submission, comment=None, title=None, discord_escape=False):
	result = ""
	if comment is not None:
		result = f"https://www.reddit.com/r/{subreddit}/comments/{submission}/_/{comment}"
	else:
		result = f"https://www.reddit.com/r/{subreddit}/comments/{submission}/_/"
	if discord_escape:
		result = f"<{result}>"
	if title is not None:
		result = f"[{title}]({result})"
	return result


def escape_username(username):
	if username is None:
		return None
	return username.replace("_", "\_")
