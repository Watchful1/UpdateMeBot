import discord_logging
import traceback
import re
from collections import defaultdict


log = discord_logging.get_logger()


from classes.subscription import Subscription


import static


def line_update_subscribe(reddit, database, line, user, bldr):
	authors = re.findall(r'(?: /?u/)([\w-]*)', line)
	subreddits = re.findall(r'(?: /?r/)(\w*)', line)

	author_name = None
	subreddit_name = None
	if len(authors) and len(subreddits):
		author_name = authors[0]
		subreddit_name = subreddits[0]

	else:
		links = re.findall(r'(?:reddit.com/r/\w*/comments/)(\w*)', line)
		if len(links):
			submission = reddit.get_submission(links[0])
			author_name = submission.author.name
			subreddit_name = submission.subreddit.display_name

	if author_name is not None and subreddit_name is not None:
		author = database.get_or_add_user(author_name)
		subreddit = database.get_or_add_subreddit(subreddit_name)

		if line.startswith("updateme"):
			recurring = False
		elif line.startswith("subscribeme"):
			recurring = True
		else:
			recurring = subreddit.default_recurring

		subscription = database.get_subscription_by_fields(user.id, author.id, subreddit.id)
		if subscription is not None:
			if subscription.recurring != recurring:
				log.info(f"Recurring changed from {subscription.recurring} to {recurring}, u/{author.name}, r/{subreddit.name}")
				bldr.append(
					f"I have updated your subscription type and will now message you {'each' if recurring else 'next'} "
					f"time u/{author.name} posts in r/{subreddit.name}  \n")
				subscription.recurring = recurring

			else:
				log.info(f"Already subscribed, u/{author.name}, r/{subreddit.name}")
				bldr.append(
					f"You had already asked me to message you {'each' if recurring else 'next'} time u/{author.name} "
					f"posts in r/{subreddit.name}  \n")

		else:
			subscription = Subscription(
				subscriber=user,
				subscribed_to=author,
				subreddit=subreddit,
				recurring=recurring
			)
			database.add_subscription(subscription)

			if not subreddit.enabled:
				log.info(f"Subscription added, u/{author.name}, r/{subreddit.name}, {recurring}, subreddit not enabled")
				bldr.append()
				---
			else:
				log.info(f"Subscription added, u/{author.name}, r/{subreddit.name}, {recurring}")
				bldr.append(
					f"I will message you {'each' if recurring else 'next'} time u/{author.name} posts in "
					f"r/{subreddit.name}  \n")


def process_message(message, reddit, database, count_string=""):
	log.info(f"{count_string}: Message u/{message.author.name} : {message.id}")
	user = database.get_or_add_user(message.author.name)
	body = message.body.lower().replace("\u00A0", " ")









	replies = defaultdict(list)

	for line in body.splitlines():
		if line.startswith("updateme") or line.startswith("subscribeme") or line.startswith("http"):
			line_update_subscribe(reddit, database, line, user)

		utility.combineDictLists(replies, MessageLineUpdateSubscribe(line, msgAuthor, datetime.utcfromtimestamp(message.created_utc)))
		utility.combineDictLists(replies, MessageLineRemove(line, msgAuthor))
		utility.combineDictLists(replies, MessageLineList(line, msgAuthor))
		utility.combineDictLists(replies, MessageLineDelete(line, msgAuthor))
		utility.combineDictLists(replies, MessageLineMute(line, msgAuthor, hasAdmin))
		utility.combineDictLists(replies, MessageLinePrompt(line, msgAuthor, hasAdmin))
		if hasAdmin:
			utility.combineDictLists(replies, MessageLineAddSubreddit(line))
			utility.combineDictLists(replies, MessageLineSubredditPM(line))

	sections = [
		{'key': "added", 'function': strings.confirmationSection},
		{'key': "updated", 'function': strings.updatedSubscriptionSection},
		{'key': "exist", 'function': strings.alreadySubscribedSection},
		{'key': "removed", 'function': strings.removeUpdatesConfirmationSection},
		{'key': "commentsDeleted", 'function': strings.deletedCommentSection},
		{'key': "couldnotadd", 'function': strings.couldNotSubscribeSection},
		{'key': "subredditsAdded", 'function': strings.subredditActivatedMessage},
		{'key': "alwaysPM", 'function': strings.subredditAlwaysPMMessage},
		{'key': "blacklist", 'function': strings.blacklistSection},
		{'key': "blacklistNot", 'function': strings.blacklistNotSection},
		{'key': "prompt", 'function': strings.promptSection},
	]

	strList = []
	for section in sections:
		if section['key'] in replies:
			strList.extend(section['function'](replies[section['key']]))
			strList.append("\n\n*****\n\n")

	# this is special cased since we need to pull in the subscriptions now, rather than during line processing
	if 'list' in replies:
		strList.extend(strings.yourUpdatesSection(database.getMySubscriptions(msgAuthor)))
		strList.append("\n\n*****\n\n")

	if len(strList) == 0:
		log.info("Nothing found in message")
		strList.append(strings.couldNotUnderstandSection)
		strList.append("\n\n*****\n\n")

	strList.append(strings.footer)

	reddit.markMessageRead(message)

	log.debug("Sending message to /u/"+str(message.author))
	if not reddit.replyMessage(message, ''.join(strList)):
		log.warning("Exception sending confirmation message")












	if bldr is None:
		bldr = ["I couldn't find anything in your message."]

	bldr.extend(utils.get_footer())
	result = reddit.reply_message(message, ''.join(bldr))
	if result != ReturnType.SUCCESS:
		if result == ReturnType.INVALID_USER:
			log.info("User banned before reply could be sent")
		else:
			raise ValueError(f"Error sending message: {result.name}")

	database.commit()


def process_messages(reddit, database):
	messages = reddit.get_messages()
	if len(messages):
		log.debug(f"Processing {len(messages)} messages")
	i = 0
	for message in messages[::-1]:
		i += 1
		if reddit.is_message(message):
			if message.author is None:
				log.info(f"Message {message.id} is a system notification")
			elif message.author.name == "reddit":
				log.info(f"Message {message.id} is from reddit, skipping")
			else:
				try:
					process_message(message, reddit, database, f"{i}/{len(messages)}")
				except Exception:
					log.warning(f"Error processing message: {message.id} : u/{message.author.name}")
					log.warning(traceback.format_exc())
				finally:
					database.commit()
		else:
			log.info(f"Object not message, skipping: {message.id}")

		try:
			reddit.mark_read(message)
		except Exception:
			log.warning(f"Error marking message read: {message.id} : {message.author.name}")
			log.warning(traceback.format_exc())

	return len(messages)
