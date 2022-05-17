import discord_logging
import traceback
from datetime import datetime

log = discord_logging.get_logger()

import counters
import utils
import static
from classes.subscription import Subscription
from classes.comment import DbComment
from praw_wrapper import ReturnType, id_from_fullname, PushshiftType


def process_comment(comment, reddit, database, count_string=""):
	if comment['author'] == static.ACCOUNT_NAME:
		log.info(f"{count_string}: Comment is from updatemebot")
		return
	if comment['author'] in static.BLACKLISTED_ACCOUNTS:
		log.info(f"{count_string}: Comment is from a blacklisted account")
		return

	counters.replies.labels(source='comment').inc()

	log.info(f"{count_string}: Processing comment {comment['id']} from u/{comment['author']}")
	body = comment['body'].lower().strip()
	use_tag = True
	if static.TRIGGER_SUBSCRIBE_LOWER in body:
		log.debug("Subscription comment")
		recurring = True
	elif static.TRIGGER_UPDATE_LOWER in body:
		log.debug("Update comment")
		recurring = False
	elif static.TRIGGER_SUBSCRIBE_ALL_LOWER in body:
		log.debug("Subscribe all comment")
		recurring = True
		use_tag = False
	else:
		log.debug("Command not in comment")
		return

	comment_result = None
	thread_id = id_from_fullname(comment['link_id'])
	subscriber = database.get_or_add_user(comment['author'])
	subreddit = database.get_or_add_subreddit(comment['subreddit'])
	db_submission = database.get_submission_by_id(thread_id)
	tag = None
	if db_submission is not None:
		author = db_submission.author
		if use_tag:
			tag = db_submission.tag
	else:
		comment_result = ReturnType.SUBMISSION_NOT_PROCESSED
		reddit_submission = reddit.get_submission(thread_id)
		try:
			author_name = reddit_submission.author.name
		except Exception:
			log.warning(f"Unable to fetch parent submission for comment: {thread_id}")
			return
		author = database.get_or_add_user(author_name)

	result_message, subscription = Subscription.create_update_subscription(
		database, subscriber, author, subreddit, recurring, tag
	)

	commented = False
	if db_submission is not None and db_submission.comment is not None:
		comment_result = ReturnType.THREAD_REPLIED
	elif subreddit.is_banned or subreddit.no_comment:
		comment_result = ReturnType.FORBIDDEN
	elif not subreddit.is_enabled:
		comment_result = ReturnType.SUBREDDIT_NOT_ENABLED
	if comment_result is None:
		reddit_comment = reddit.get_comment(comment['id'])
		count_subscriptions = database.get_count_subscriptions_for_author_subreddit(author, subreddit, tag)
		db_comment = DbComment(
			comment_id=None,
			submission=db_submission,
			subscriber=subscriber,
			author=author,
			subreddit=subreddit,
			recurring=recurring,
			current_count=count_subscriptions,
			tag=tag
		)

		bldr = utils.get_footer(db_comment.render_comment(
			count_subscriptions=count_subscriptions,
			pushshift_minutes=reddit.get_effective_pushshift_lag()
		))

		result_id, comment_result = reddit.reply_comment(reddit_comment, ''.join(bldr))

		if comment_result in (
				ReturnType.INVALID_USER,
				ReturnType.USER_DOESNT_EXIST,
				ReturnType.THREAD_LOCKED,
				ReturnType.DELETED_COMMENT,
				ReturnType.RATELIMIT):
			log.info(f"Unable to reply as comment: {comment_result.name}")
			counters.api_responses.labels(call='comment', type=comment_result.name.lower()).inc()

		elif comment_result == ReturnType.FORBIDDEN:
			log.warning(f"Banned in subreddit, saving: {subreddit.name}")
			subreddit.is_banned = True
			counters.api_responses.labels(call='comment', type=comment_result.name.lower()).inc()

		else:
			if comment_result == ReturnType.NOTHING_RETURNED:
				result_id = "QUARANTINED"
				log.warning(f"Opting in to quarantined subreddit: {subreddit.name}")
				reddit.quarantine_opt_in(subreddit.name)
				counters.api_responses.labels(call='comment', type=comment_result.name.lower()).inc()

			if result_id is None:
				log.warning(f"Got comment ID of None when replying in subreddit, saving: {subreddit.name}")
				subreddit.is_banned = True
				comment_result = ReturnType.FORBIDDEN
				counters.api_responses.labels(call='comment', type=comment_result.name.lower()).inc()

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
		pushshift_lag = reddit.get_effective_pushshift_lag()
		if pushshift_lag > 15:
			bldr.append("There is a ")
			if pushshift_lag > 60:
				bldr.append(str(int(round(pushshift_lag / 60, 1))))
				bldr.append(" hour")
			else:
				bldr.append(str(pushshift_lag))
				bldr.append(" minute")
			bldr.append(" delay fetching comments.")
			bldr.append("\n\n")

		bldr.append(result_message)
		bldr = utils.get_footer(bldr)

		result = reddit.send_message(subscriber.name, "UpdateMeBot Confirmation", ''.join(bldr))
		if result != ReturnType.SUCCESS:
			if result == ReturnType.NOT_WHITELISTED_BY_USER_MESSAGE:
				log.info(f"Unable to send message: {result.name}")
			else:
				log.warning(f"Unable to send message: {result.name}")
			counters.api_responses.labels(call='confmsg', type=result.name.lower()).inc()


def process_comments(reddit, database):
	comments = reddit.get_keyword_comments(static.TRIGGER_COMBINED, database.get_or_init_datetime("comment_timestamp"))

	counters.pushshift_delay.labels(client="prod").set(reddit.pushshift_prod_client.lag_minutes())
	counters.pushshift_delay.labels(client="beta").set(reddit.pushshift_beta_client.lag_minutes())
	counters.pushshift_delay.labels(client="auto").set(reddit.get_effective_pushshift_lag())

	if reddit.recent_pushshift_client == PushshiftType.PROD:
		counters.pushshift_client.labels(client="prod").set(1)
		counters.pushshift_client.labels(client="beta").set(0)
	elif reddit.recent_pushshift_client == PushshiftType.BETA:
		counters.pushshift_client.labels(client="prod").set(0)
		counters.pushshift_client.labels(client="beta").set(1)
	else:
		counters.pushshift_client.labels(client="prod").set(0)
		counters.pushshift_client.labels(client="beta").set(0)

	counters.pushshift_failed.labels(client="prod").set(1 if reddit.pushshift_prod_client.failed() else 0)
	counters.pushshift_failed.labels(client="beta").set(1 if reddit.pushshift_beta_client.failed() else 0)

	counters.pushshift_seconds.labels("prod").observe(reddit.pushshift_prod_client.request_seconds)
	counters.pushshift_seconds.labels("beta").observe(reddit.pushshift_beta_client.request_seconds)

	if len(comments):
		log.debug(f"Processing {len(comments)} comments")
	i = 0
	for comment in comments[::-1]:
		i += 1
		mark_read = True
		try:
			process_comment(comment, reddit, database, f"{i}/{len(comments)}")
		except Exception as err:
			mark_read = not utils.process_error(
				f"Error processing comment: {comment['id']} : {comment['author']}",
				err, traceback.format_exc()
			)

		if mark_read:
			reddit.mark_keyword_comment_processed(comment['id'])
			database.save_datetime("comment_timestamp", datetime.utcfromtimestamp(comment['created_utc']))
		else:
			return i

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
