import discord_logging
import traceback
import re


log = discord_logging.get_logger()


import counters
from classes.subscription import Subscription
from praw_wrapper.reddit import ReturnType
import static
import utils


def line_update_subscribe(line, user, bldr, database, reddit):
	authors = re.findall(r'(?:[ +]/?u/)([\w-]+)', line)
	subreddits = re.findall(r'(?:[ +]/?r/)([\w-]+)', line)
	tags = re.findall(r'(?:<)(.+)(?:>)', line)
	is_all = "-all" in line

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

	elif is_all and len(subreddits):
		case_is_user_supplied = True
		subreddit_name = subreddits[0]

	else:
		links = re.findall(r'(?:reddit.com/r/\w+/comments/)(\w+)', line)

		if len(links):
			db_submission = database.get_submission_by_id(links[0])
			tag = None
			if db_submission is not None:
				author_name = db_submission.author.name
				subreddit_name = db_submission.subreddit.name
				if db_submission.subreddit.tag_enabled:
					tag = db_submission.tag
			else:
				reddit_submission = reddit.get_submission(links[0])
				try:
					author_name = reddit_submission.author.name
					subreddit_name = reddit_submission.subreddit.display_name
				except Exception:
					log.warning(f"Unable to fetch submission for link message: {links[0]}")
					return

	if (author_name is not None or is_all) and subreddit_name is not None:
		if is_all:
			author = None
		else:
			author = database.get_user(author_name)
			if author is None:
				if not reddit.redditor_exists(author_name):
					log.info(f"u/{author_name} doesn't exist when creating subscription")
					bldr.append(f"It doesn't look like u/{author_name} exists, are you sure you spelled it right?")
					return
				else:
					author = database.get_or_add_user(author_name, case_is_user_supplied)
		subreddit = database.get_subreddit(subreddit_name)
		if subreddit is None:
			if subreddit_name == 'subreddit' or subreddit_name == 'subreddi':
				log.info(f"r/{subreddit_name} bad subreddit")
				bldr.append(
					f"You've requested updates for r/{subreddit_name}, you probably forgot to update the subreddit name")
				return
			elif not reddit.subreddit_exists(subreddit_name):
				log.info(f"r/{subreddit_name} doesn't exist when creating subscription")
				bldr.append(f"It doesn't look like r/{subreddit_name} exists, are you sure you spelled it right?")
				return
			else:
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
				if subscription.author is None:
					bldr.append(
						f"Removed your {'subscription' if subscription.recurring else 'update'} to "
						f" r/{subscription.subreddit.name}  \n")
				else:
					bldr.append(
						f"Removed your {'subscription' if subscription.recurring else 'update'} to "
						f"u/{subscription.author.name} in r/{subscription.subreddit.name}  \n")

			count_removed = database.delete_user_subscriptions(user)
			log.info(f"Removed all {count_removed} subscriptions for u/{user.name}")
			if count_removed != len(subscriptions):
				log.warning(f"Error removing subscriptions for u/{user.name} : {len(subscriptions)} : {count_removed}")

	else:
		users = re.findall(r'(?:/?u/)([\w-]+)', line)
		subs = re.findall(r'(?:/?r/)([\w-]+)', line)
		tags = re.findall(r'(?:<)(.+)(?:>)', line)
		is_all = "-all" in line

		tag = None
		if len(tags):
			tag = tags[0]

		if (not len(users) and not is_all) or not len(subs):
			log.info("Couldn't find anything in removal message")
			bldr.append("I couldn't figure out what subscription to remove")

		else:
			subreddit = database.get_subreddit(subs[0])
			if subreddit is None:
				log.info(f"Could not find subreddit r/{subs[0]} for removal")
				bldr.append(f"I couldn't find any subscriptions in r/{subs[0]} to remove")

			else:
				if is_all:
					subscription = database.get_subscription_by_fields(user, None, subreddit, tag)
					if subscription is None:
						if tag is None and database.get_count_tagged_subscriptions_by_fields(user, None, subreddit):
							log.info(f"Removed tagged subscriptions for u/{user.name} in r/{subreddit.name}")
							bldr.append(f"I've removed all your global tagged subscriptions in r/{subreddit.name}")
							database.delete_tagged_subreddit_author_subscriptions(user, None, subreddit)

						else:
							log.info(
								f"Could not find subscription for u/{user.name} "
								f"{('with tag '+tag+' ' if tag is not None else '')}in r/{subreddit.name} to remove")
							bldr.append(
								f"I couldn't find a subscription for you "
								f"{('with tag <'+tag+'> ' if tag is not None else '')}in r/{subreddit.name} to remove")

					else:
						log.info(
							f"Removed {'subscription' if subscription.recurring else 'update'} for u/{user.name} "
							f" {('with tag '+tag if tag is not None else '')}in r/{subscription.subreddit.name}")
						bldr.append(
							f"I removed your {'subscription' if subscription.recurring else 'update'} "
							f"in r/{subscription.subreddit.name}{(' with tag <'+tag+'>' if tag is not None else '')}")
						database.delete_subscription(subscription)
				else:
					author = database.get_user(users[0])
					if author is None:
						log.info(f"Could not find author u/{users[0]} for removal")
						bldr.append(f"I couldn't find any subscriptions to u/{users[0]} in r/{subs[0]} to remove")

					else:
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
									f"{('with tag <'+tag+'>' if tag is not None else '')}in r/{subreddit.name} to remove")

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
			if subscription.author is None:
				bldr.append(" post")
			else:
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


def line_abbrev(line, user, bldr, database, reddit):
	if line.startswith("short"):
		user.short_notifs = True
		log.info("Change to short notifs")
		bldr.append("You'll now get shortened notifications. Reply `long` to revert this")

	elif line.startswith("long"):
		user.short_notifs = False
		log.info("Change to long notifs")
		bldr.append("You'll now get normal notifications. Reply `short` to revert this")


def line_add_sub(line, bldr, database):
	subs = re.findall(r'(?:/?r/)([\w-]+)', line)
	if len(subs):
		subreddit = database.get_or_add_subreddit(subs[0])
		count_subscriptions = database.get_count_subscriptions_for_subreddit(subreddit)
		if "subscribe" in line:
			recurring = True
		else:
			recurring = False
		if subreddit.is_enabled:
			subreddit.default_recurring = recurring
			bldr.append(f"Changed r/{subreddit.name} to ")
			bldr.append('subscribe' if recurring else 'update')
		else:
			log.info(
				f"Activating r/{subreddit.name} with {count_subscriptions} subscriptions as "
				f"{'subscription' if recurring else 'update'}")
			subreddit.is_enabled = True
			subreddit.last_scanned = utils.datetime_now()
			subreddit.date_enabled = utils.datetime_now()
			subreddit.default_recurring = recurring
			bldr.append(f"Activated r/{subreddit.name} with {count_subscriptions} subscriptions as ")
			bldr.append('subscribe' if recurring else 'update')
		if subreddit.posts_per_hour is None:
			subreddit.posts_per_hour = 50


def line_remove_sub(line, bldr, database):
	subs = re.findall(r'(?:/?r/)([\w-]+)', line)
	if len(subs):
		subreddit = database.get_subreddit(subs[0])
		if subreddit is None:
			bldr.append(f"Subreddit r/{subs[0]} not found")
		elif subreddit.is_enabled:
			subreddit.is_enabled = False
			count_subscriptions = database.get_count_subscriptions_for_subreddit(subreddit)
			bldr.append(f"Subreddit r/{subs[0]} with {count_subscriptions} subscriptions disabled")
		else:
			bldr.append(f"Subreddit r/{subs[0]} is already disabled")


def line_blacklist_sub(line, bldr, database):
	subs = re.findall(r'(?:/?r/)([\w-]+)', line)
	if len(subs):
		subreddit = database.get_subreddit(subs[0])
		if subreddit is None:
			bldr.append(f"Subreddit r/{subs[0]} not found")
			return
		if subreddit.is_enabled:
			subreddit.is_enabled = False

		subreddit.is_blacklisted = True
		count_subscriptions = database.delete_subreddit_subscriptions(subreddit)
		bldr.append(f"Subreddit r/{subs[0]} blacklisted and {count_subscriptions} subscriptions deleted")
		log.info(f"Subreddit blacklisted: r/{subs[0]}")


def line_mute_sub(line, bldr, database):
	subs = re.findall(r'(?:/?r/)([\w-]+)', line)
	muted_date = re.findall(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
	if len(subs) and len(muted_date):
		subreddit = database.get_subreddit(subs[0])
		if subreddit is None:
			bldr.append(f"Subreddit r/{subs[0]} not found")
			return

		muted_datetime = utils.parse_datetime_string(muted_date[0])
		if muted_datetime is None:
			bldr.append(f"Unable to parse date {muted_date[0]}")
			return

		subreddit.muted_until = muted_datetime

		bldr.append(f"Subreddit r/{subs[0]} muted until {utils.get_datetime_string(muted_datetime)}")
		log.info(f"Subreddit muted: r/{subs[0]} : {utils.get_datetime_string(muted_datetime)}")


def line_purge_user(line, bldr, database):
	users = re.findall(r'(?: /?u/)([\w-]+)', line)
	if len(users):
		user_name = users[0]
		user = database.get_or_add_user(user_name, case_is_user_supplied=True)
		log.info(f"Force purging user u/{user_name} : {user.id}")
		database.purge_user(user, True)
		bldr.append(f"Force purged user u/{user_name}")


def process_message(message, reddit, database, count_string=""):
	log.info(f"{count_string}: Message u/{message.author.name} : {message.id}")
	user = database.get_or_add_user(message.author.name)
	if user.first_failure is not None:
		user.first_failure = None
	body = message.body.lower().replace("\u00A0", " ")

	counters.replies.labels(source='message').inc()

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
		elif line.startswith("short") or line.startswith("long"):
			line_abbrev(line, user, bldr, database, reddit)
		elif user.name == static.OWNER:
			if line.startswith("addsubreddit"):
				line_add_sub(line, bldr, database)
			elif line.startswith("subredditremove"):
				line_remove_sub(line, bldr, database)
			elif line.startswith("subredditblacklist"):
				line_blacklist_sub(line, bldr, database)
			elif line.startswith("subredditmute"):
				line_mute_sub(line, bldr, database)
			elif line.startswith("purgeuser"):
				line_purge_user(line, bldr, database)

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
			counters.api_responses.labels(call='replmsg', type=result.name.lower()).inc()
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
		mark_read = True
		if reddit.is_message(message):
			if message.author is None:
				log.info(f"Message {message.id} is a system notification")
			elif message.author.name.lower() in {"reddit", "remindmebot"}:
				log.info(f"Message {message.id} is from reddit, skipping")
			else:
				try:
					process_message(message, reddit, database, f"{i}/{len(messages)}")
				except Exception as err:
					mark_read = not utils.process_error(
						f"Error processing message: {message.id} : u/{message.author.name}",
						err, traceback.format_exc()
					)
				finally:
					database.commit()
		else:
			log.info(f"Object not message, skipping: {message.id}")

		if mark_read:
			try:
				reddit.mark_read(message)
			except Exception as err:
				utils.process_error(
					f"Error marking message read: {message.id} : {message.author.name}",
					err, traceback.format_exc()
				)

	return len(messages)
