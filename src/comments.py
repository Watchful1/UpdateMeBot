import discord_logging
import traceback
from datetime import datetime

log = discord_logging.get_logger()

import utils
import static
from classes.subscription import Subscription
from classes.comment import DbComment
from classes.enums import ReturnType


# def database_set_seen(database, comment_seen):
# 	database.save_keystore("comment_timestamp", comment_seen.strftime("%Y-%m-%d %H:%M:%S"))
#
#
# def database_get_seen(database):
# 	result = database.get_keystore("comment_timestamp")
# 	if result is None:
# 		log.warning("Comment time not in database, returning now")
# 		now = utils.datetime_now()
# 		database_set_seen(database, now)
# 		return now
# 	return datetime.strptime(result, "%Y-%m-%d %H:%M:%S")


def process_comment(comment, reddit, database, count_string=""):
	if comment['author'] == static.ACCOUNT_NAME:
		log.debug("Comment is from updatemebot")
		return
	if comment['author'] in static.BLACKLISTED_ACCOUNTS:
		log.debug("Comment is from a blacklisted account")
		return

	log.info(f"{count_string}: Processing comment {comment['id']} from u/{comment['author']}")
	body = comment['body'].lower().strip()
	if static.TRIGGER_SUBSCRIBE_LOWER in body:
		log.debug("Subscription comment")
		recurring = True
	elif static.TRIGGER_UPDATE_LOWER in body:
		log.debug("Update comment")
		recurring = False
	else:
		log.debug("Command not in comment")
		return

	comment_result = None
	thread_id = utils.id_from_fullname(comment['link_id'])
	subscriber = database.get_or_add_user(comment['author'])
	subreddit = database.get_or_add_subreddit(comment['subreddit'])
	db_submission = database.get_submission_by_id(thread_id)
	if db_submission is not None:
		author_name = db_submission.author_name
	else:
		comment_result = ReturnType.SUBMISSION_NOT_PROCESSED
		reddit_submission = reddit.get_submission(thread_id)
		try:
			author_name = reddit_submission.author.name
		except Exception:
			log.warning(f"Unable to fetch parent submission for comment: {thread_id}")
			return

	author = database.get_or_add_user(author_name)
	subscription = database.get_subscription_by_fields(subscriber, author, subreddit)
	if subscription is not None:
		if subscription.recurring == recurring:
			log.info(
				f"u/{subscriber.name} already {'subscribed' if recurring else 'updated'} to u/{author.name} in "
				f"r/{subreddit.name}")
			message_result = \
				f"You had already asked me to message you {'each' if recurring else 'next'} time u/{author.name} " \
				f"posts in r/{subreddit.name}"

		else:
			log.info(
				f"u/{subscriber.name} changed from {'update to subscription' if recurring else 'subscription to update'}"
				f" for u/{author.name} in r/{subreddit.name}")
			message_result = \
				f"I have updated your subscription type and will now message you {'each' if recurring else 'next'} " \
				f"time u/{author.name} posts in r/{subreddit.name}"
			subscription.recurring = recurring

	else:
		subscription = Subscription(
			subscriber=subscriber,
			author=author,
			subreddit=subreddit,
			recurring=recurring
		)
		database.add_subscription(subscription)

		if not subreddit.is_enabled:
			log.info(f"Subscription added, u/{author.name}, r/{subreddit.name}, {recurring}, subreddit not enabled")
			message_result = \
				f"Subreddit r/{subreddit.name} is not being tracked by the bot. More details [here]" \
				f"({static.TRACKING_INFO_URL})"
			comment_result = ReturnType.SUBREDDIT_NOT_ENABLED
			utils.check_update_disabled_subreddit(database, subreddit)
		else:
			log.info(f"Subscription added, u/{author.name}, r/{subreddit.name}, {recurring}")
			message_result = \
				f"I will message you {'each' if recurring else 'next'} time u/{author.name} posts in " \
				f"r/{subreddit.name}"

	commented = False
	if db_submission is not None and db_submission.comment is not None:
		comment_result = ReturnType.THREAD_REPLIED
	elif subreddit.is_banned:
		comment_result = ReturnType.FORBIDDEN
	if comment_result is None:
		reddit_comment = reddit.get_comment(comment['id'])
		count_subscriptions = database.get_count_subscriptions_for_author_subreddit(author, subreddit)
		db_comment = DbComment(
			comment_id=None,
			submission=db_submission,
			subscriber=subscriber,
			author=author,
			subreddit=subreddit,
			recurring=recurring,
			current_count=count_subscriptions
		)

		bldr = utils.get_footer(db_comment.render_comment(
			count_subscriptions=count_subscriptions,
			pushshift_minutes=reddit.pushshift_lag
		))

		result_id, comment_result = reddit.reply_comment(reddit_comment, ''.join(bldr))

		if comment_result in (
				ReturnType.INVALID_USER,
				ReturnType.USER_DOESNT_EXIST,
				ReturnType.THREAD_LOCKED,
				ReturnType.DELETED_COMMENT,
				ReturnType.RATELIMIT):
			log.info(f"Unable to reply as comment: {comment_result.name}")

		elif comment_result == ReturnType.FORBIDDEN:
			log.warning(f"Banned in subreddit, saving: {subreddit.name}")
			subreddit.is_banned = True

		else:
			if comment_result == ReturnType.NOTHING_RETURNED:
				result_id = "QUARANTINED"
				log.warning(f"Opting in to quarantined subreddit: {subreddit.name}")
				reddit.quarantine_opt_in(subreddit.name)

			if result_id is None:
				log.warning(f"Got comment ID of None when replying to {comment['id']}")
				comment_result = ReturnType.FORBIDDEN

			else:
				log.info(
					f"Subscription created: {subscription.id}, replied as comment: {result_id}")

				if comment_result != ReturnType.QUARANTINED:
					db_comment.comment_id = result_id
					database.add_comment(db_comment)
				commented = True

	if not commented:
		log.info(
			f"Subscription created: {subscription.id}, replying as message: {comment_result.name}")

		bldr = utils.str_bldr()
		if reddit.pushshift_lag > 15:
			bldr.append("There is a ")
			if reddit.pushshift_lag > 60:
				bldr.append(str(int(round(reddit.pushshift_lag / 60, 1))))
				bldr.append(" hour")
			else:
				bldr.append(str(reddit.pushshift_lag))
				bldr.append(" minute")
			bldr.append(" delay fetching comments.")
			bldr.append("\n\n")

		bldr.append(message_result)
		bldr = utils.get_footer(bldr)

		result = reddit.send_message(author.name, "UpdateMeBot Confirmation", ''.join(bldr))
		if result != ReturnType.SUCCESS:
			log.warning(f"Unable to send message: {result.name}")


def process_comments(reddit, database):
	comments = reddit.get_keyword_comments(static.TRIGGER_COMBINED, database.get_or_init_datetime("comment_timestamp"))
	if len(comments):
		log.debug(f"Processing {len(comments)} comments")
	i = 0
	for comment in comments[::-1]:
		i += 1
		try:
			process_comment(comment, reddit, database, f"{i}/{len(comments)}")
		except Exception:
			log.warning(f"Error processing comment: {comment['id']} : {comment['author']}")
			log.warning(traceback.format_exc())

		reddit.mark_keyword_comment_processed(comment['id'])
		database.save_keystore("comment_timestamp", datetime.utcfromtimestamp(comment['created_utc']))

	return len(comments)


def update_comments(reddit, database):
	count_incorrect = database.get_pending_incorrect_comments()

	i = 0
	if count_incorrect > 0:
		incorrect_items = database.get_incorrect_comments(utils.requests_available(count_incorrect))
		for db_comment, new_count in incorrect_items:
			i += 1
			log.info(
				f"{i}/{len(incorrect_items)}/{count_incorrect}: Updating comment : "
				f"{db_comment.comment_id} : {db_comment.current_count}/{new_count}")

			bldr = utils.get_footer(db_comment.render_comment(count_subscriptions=new_count))
			reddit.edit_comment(''.join(bldr), comment_id=db_comment.comment_id)
			db_comment.current_count = new_count

	else:
		log.debug("No incorrect comments")

	return i
