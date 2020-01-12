import discord_logging
import traceback
from collections import defaultdict


log = discord_logging.get_logger()


import static


def process_message(message, reddit, database, count_string=""):
	log.info(f"{count_string}: Message u/{message.author.name} : {message.id}")
	user = database.get_or_add_user(message.author.name)
	user.recurring_sent = 0
	body = message.body.lower()

	bldr = None








	replies = defaultdict(list)
	msgAuthor = str(message.author).lower()
	hasAdmin = msgAuthor == static.OWNER_NAME.lower()

	for line in message.body.lower().splitlines():
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
