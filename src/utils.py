from datetime import datetime
import discord_logging
import re
import urllib.parse


log = discord_logging.get_logger()


import static


def datetime_now():
	return datetime.utcnow().replace(microsecond=0)


def html_encode(message):
	return urllib.parse.quote(message, safe='')


def build_message_link(recipient, subject, content=None):
	base = "https://np.reddit.com/message/compose/?"
	bldr = str_bldr()
	bldr.append(f"to={recipient}")
	bldr.append(f"subject={html_encode(subject)}")
	if content is not None:
		bldr.append(f"message={html_encode(content)}")

	return base + '&'.join(bldr)


def replace_np(link):
	return re.sub(r"(www|old|new)\.reddit\.com", "np.reddit.com", link)


def get_footer(bldr=None):
	if bldr is None:
		bldr = []
	bldr.append("\n\n")
	bldr.append("*****")
	bldr.append("\n\n")

	bldr.append("|[^(Info)](")
	bldr.append(replace_np(static.INFO_POST))
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
