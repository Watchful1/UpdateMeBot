import discord_logging
import traceback
import re


log = discord_logging.get_logger()


from classes.subscription import Subscription
from classes.enums import ReturnType
import static
import utils


def line_update_subscribe(line, user, bldr, database, reddit):
	authors = re.findall(r'(?: /?u/)([\w-]+)', line)
	subreddits = re.findall(r'(?: /?r/)(\w+)', line)
	tags = re.findall(r'(?:<)(.+)(?:>)', line)

	tag = None
	if len(tags):
		tag = tags[0]

	author_name = None
	subreddit_name = None
	case_is_user_supplied = False
	if len(authors) and len(subreddits):
		case_is_user_supplied = True
		author_name = authors[0]
		subreddit_name = subreddits[0]

	else:
		links = re.findall(r'(?:reddit.com/r/\w+/comments/)(\w+)', line)

		if len(links):
			db_submission = database.get_submission_by_id(links[0])
			tag = None
			if db_submission is not None:
				author_name = db_submission.author_name
				subreddit_name = db_submission.subreddit.name
				if db_submission.subreddit.tag_enabled:
					tag = db_submission.tag
			else:
				reddit_submission = reddit.get_submission(links[0])
				try:
					author_name = reddit_submission.author.name
					subreddit_name = reddit_submission.subreddit.display_name
				except Exception:
					log.warning(f"Unable to fetch submission for link memssage: {links[0]}")
					return

	if author_name is not None and subreddit_name is not None:
		author = database.get_or_add_user(author_name, case_is_user_supplied)
		subreddit = database.get_or_add_subreddit(subreddit_name, case_is_user_supplied)

		if line.startswith(static.TRIGGER_UPDATE_LOWER):
			recurring = False
		elif line.startswith(static.TRIGGER_SUBSCRIBE_LOWER):
			recurring = True
		else:
			recurring = subreddit.default_recurring

		result_message, subscription = Subscription.create_update_subscription(
			database, user, author, subreddit, recurring, tag
		)
		bldr.append(result_message)


def line_remove(line, user, bldr, database):
	if line.startswith("removeall"):
		subscriptions = database.get_user_subscriptions(user)
		if not len(subscriptions):
			log.info(f"u/{user.name} doesn't have any subscriptions to remove")
			bldr.append("You don't have any subscriptions to remove")

		else:
			for subscription in subscriptions:
				bldr.append(
					f"Removed your {'subscription' if subscription.recurring else 'update'} to "
					f"u/{subscription.author.name} in r/{subscription.subreddit.name}")

			count_removed = database.delete_user_subscriptions(user)
			if count_removed != len(subscriptions):
				log.warning(f"Error removing subscriptions for u/{user.name} : {len(subscriptions)} : {count_removed}")

	else:
		users = re.findall(r'(?:/?u/)([\w-]+)', line)
		subs = re.findall(r'(?:/?r/)(\w+)', line)
		tags = re.findall(r'(?:<)(.+)(?:>)', line)

		tag = None
		if len(tags):
			tag = tags[0]

		if not len(users) or not len(subs):
			log.info("Couldn't find anything in removal message")
			bldr.append("I couldn't figure out what subscription to remove")

		else:
			author = database.get_user(users[0])
			subreddit = database.get_subreddit(subs[0])
			subscription = None
			if author is not None and subreddit is not None:
				subscription = database.get_subscription_by_fields(user, author, subreddit, tag)

			if subscription is None:
				if tag is None and database.get_count_tagged_subscriptions_by_fields(user, author, subreddit):
					log.info(f"Removed tagged subscriptions for u/{user.name} to u/{author.name} in r/{subreddit.name}")
					bldr.append(f"I've removed all your tagged subscriptions to u/{author.name} in r/{subreddit.name}")
					database.delete_tagged_subreddit_author_subscriptions(user, author, subreddit)

				else:
					log.info(
						f"Could not find subscription for u/{user.name} to u/{author.name} "
						f"{('with tag '+tag if tag is not None else '')}in r/{subreddit.name} to remove")
					bldr.append(
						f"I couldn't find a subscription for you to u/{author.name} "
						f"{('with tag '+tag+'>' if tag is not None else '')}in r/{subreddit.name} to remove")

			else:
				log.info(
					f"Removed {'subscription' if subscription.recurring else 'update'} for u/{user.name} to "
					f"u/{subscription.author.name} {('with tag '+tag if tag is not None else '')}in "
					f"r/{subscription.subreddit.name}")
				bldr.append(
					f"I removed your {'subscription' if subscription.recurring else 'update'} to "
					f"u/{subscription.author.name} in r/{subscription.subreddit.name}"
					f"{(' with tag <'+tag+'>' if tag is not None else '')}")
				database.delete_subscription(subscription)


def line_delete(line, user, bldr, database, reddit):
	ids = re.findall(r'delete\s+(\w+)', line)

	if len(ids) == 0:
		log.info("Couldn't find a thread id to delete")
		return
	else:
		db_comment = database.get_comment_by_thread(ids[0])
		if db_comment is not None:
			if db_comment.subscriber.name == user.name:
				comment = reddit.get_comment(db_comment.comment_id)
				if not reddit.delete_comment(comment):
					log.debug(f"Unable to delete comment: {db_comment.comment_id}")
					bldr.append("Something went wrong deleting the comment")
				else:
					database.delete_comment(db_comment)
					log.debug(f"Deleted comment: {db_comment.comment_id}")
					bldr.append("Comment deleted.")
			else:
				log.debug(f"Bot wasn't replying to owner: {db_comment.subscriber.name} : {user.name}")
				bldr.append("It looks like the bot wasn't replying to you.")
		else:
			log.debug(f"Comment doesn't exist: {ids[0]}")
			bldr.append("This comment doesn't exist or was already deleted.")


def line_list(user, bldr, database):
	subscriptions = database.get_user_subscriptions(user)
	if not len(subscriptions):
		log.info(f"u/{user.name} doesn't have any subscriptions to list")
		bldr.append("You don't have any subscriptions")

	else:
		log.info(f"Listing subscriptions for u/{user.name}")
		bldr.append("I'll message you for each of the following:  \n")
		for subscription in subscriptions:
			if subscription.recurring:
				bldr.append("Each")
			else:
				bldr.append("Next")
			bldr.append(" time u/")
			bldr.append(subscription.author.name)
			bldr.append(" posts")
			if subscription.tag is not None:
				bldr.append(" tagged <")
				bldr.append(subscription.tag)
				bldr.append(">")
			bldr.append(" in r/")
			bldr.append(subscription.subreddit.name)
			bldr.append("  \n")


def line_add_sub(line, bldr, database):
	subs = re.findall(r'(?:/?r/)(\w+)', line)
	if len(subs):
		subreddit = database.get_or_add_subreddit(subs[0])
		count_subscriptions = database.get_count_subscriptions_for_subreddit(subreddit)
		if "subscribe" in line:
			recurring = True
		else:
			recurring = False
		log.warning(
			f"Activating r/{subreddit.name} with {count_subscriptions} subscriptions as "
			f"{'subscription' if recurring else 'update'}")
		subreddit.is_enabled = True
		subreddit.last_scanned = utils.datetime_now()
		subreddit.default_recurring = recurring
		bldr.append(f"Activated r/{subreddit.name} with {count_subscriptions} subscriptions as ")
		bldr.append('subscribe' if recurring else 'update')


def process_message(message, reddit, database, count_string=""):
	log.info(f"{count_string}: Message u/{message.author.name} : {message.id}")
	user = database.get_or_add_user(message.author.name)
	body = message.body.lower().replace("\u00A0", " ")

	bldr = []
	append_list = False
	current_len = 0
	for line in body.splitlines():
		if line.startswith(static.TRIGGER_UPDATE_LOWER) or line.startswith(static.TRIGGER_SUBSCRIBE_LOWER) \
				or line.startswith("http"):
			line_update_subscribe(line, user, bldr, database, reddit)
		elif line.startswith("remove"):
			line_remove(line, user, bldr, database)
		elif line.startswith("delete"):
			line_delete(line, user, bldr, database, reddit)
		elif line.startswith("mysubscriptions") or line.startswith("myupdates"):
			append_list = True
		elif user.name == static.OWNER:
			if line.startswith("addsubreddit"):
				line_add_sub(line, bldr, database)

		if len(bldr) > current_len:
			current_len = len(bldr)
			bldr.append("  \n")

	if append_list:
		line_list(user, bldr, database)

	if not len(bldr):
		log.info("Nothing found in message")
		bldr.append("I couldn't find anything in your message.")

	bldr.extend(utils.get_footer())
	full_message = ''.join(bldr)
	replies = []
	if len(full_message) > 9500:
		partial_message = []
		partial_length = 0
		for line in full_message.split("\n"):
			partial_message.append(line)
			partial_message.append("\n")
			partial_length += len(line) + 1
			if partial_length > 9500:
				replies.append(''.join(partial_message))
				partial_message = []
				partial_length = 0

		if len(partial_message):
			replies.append(''.join(partial_message))
	else:
		replies.append(full_message)

	for reply in replies:
		result = reddit.reply_message(message, reply)
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
