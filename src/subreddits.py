import discord_logging
import math
import traceback
import time
import prawcore
from datetime import datetime, timedelta

log = discord_logging.get_logger()

import counters
import utils
import static
from classes.submission import Submission
from classes.notification import Notification
from classes.enums import SubredditPromptType


def get_blacklist_mute_message(subreddit_name):
	blacklist_message_link = utils.build_message_link(
		static.ACCOUNT_NAME, 'Blacklist sub', f'SubredditBlacklist r/{subreddit_name}'
	)
	mute_message_link = utils.build_message_link(
		static.ACCOUNT_NAME, 'Mute sub',
		f'SubredditMute r/{subreddit_name} {utils.get_datetime_string(utils.datetime_now() + timedelta(days=2))}'
	)
	return f"[Blacklist](<{blacklist_message_link}>) : [Mute](<{mute_message_link}>)"


def subreddit_posts_per_hour(reddit, subreddit_name):
	count = 0
	oldest_submission = utils.datetime_now()
	updated_name = None
	try:
		name_mismatch = False
		for submission in reddit.get_subreddit_submissions(subreddit_name):
			count += 1
			if not name_mismatch:
				if submission.subreddit.display_name != subreddit_name:
					if submission.subreddit.display_name.lower() == subreddit_name:
						updated_name = submission.subreddit.display_name
						log.info(
							f"Updated subreddit name from {subreddit_name} to {submission.subreddit.display_name}")
					else:
						log.warning(
							f"Subreddit name doesn't match when profiling: {subreddit_name}, "
							f"{submission.subreddit.display_name}")
					name_mismatch = True
			submission_created = datetime.utcfromtimestamp(submission.created_utc)
			if submission_created < oldest_submission:
				oldest_submission = submission_created
			if count >= 50:
				break
	except (prawcore.exceptions.Redirect, prawcore.exceptions.NotFound):
		log.warning(f"Subreddit r/{subreddit_name} doesn't exist when profiling")
		return -1, updated_name
	except prawcore.exceptions.Forbidden:
		log.info(f"Subreddit r/{subreddit_name} forbidden when profiling")
		return -2, updated_name

	if count == 0:
		return 1, updated_name

	hours = math.trunc((utils.datetime_now() - oldest_submission).total_seconds() / (60 * 60))
	if hours == 0:
		posts_per_hour = count
	else:
		posts_per_hour = int(math.ceil(count / hours))

	return posts_per_hour, updated_name


def profile_subreddits(reddit, database, limit=10):
	changes_made = False
	for subreddit in database.get_unprofiled_subreddits(limit=limit):
		try:
			posts_per_hour, updated_name = subreddit_posts_per_hour(reddit, subreddit.name)
			if updated_name is not None:
				subreddit.name = updated_name
			if posts_per_hour == -2:
				if not reddit.quarantine_opt_in(subreddit.name):
					if subreddit.last_profiled is None or subreddit.last_profiled - timedelta(days=120) > utils.datetime_now():
						if subreddit.is_enabled:
							log.warning(f"Unable to opt in to enabled subreddit: r/{subreddit.name} : {get_blacklist_mute_message(subreddit.name)}")
						else:
							log.warning(f"Can't opt in to r/{subreddit.name}, blacklisting")
							subreddit.is_blacklisted = True
					else:
						subreddit.muted_until = utils.datetime_now() + timedelta(days=1)
						log.info(f"Muting until: {utils.get_datetime_string(subreddit.muted_until)}")
				continue
			if posts_per_hour == -1:
				log.warning(f"r/{subreddit.name} doesn't exist, blacklisting")
				subreddit.is_blacklisted = True
			if subreddit.posts_per_hour != posts_per_hour:
				log.info(f"Profiled subreddit {subreddit.name} from {subreddit.posts_per_hour} to {posts_per_hour}")
			subreddit.posts_per_hour = posts_per_hour
			subreddit.last_profiled = utils.datetime_now()
			changes_made = True
		except Exception as err:
			utils.process_error(
				f"Error profiling subreddit: {subreddit.name}",
				err, traceback.format_exc()
			)

	if changes_made:
		database.commit()


def unmute_subreddits(database):
	for subreddit in database.get_unmute_subreddits():
		log.warning(f"Unmuting r/{subreddit.name}")
		subreddit.muted_until = None
		subreddit.is_enabled = True
		database.commit()


def recheck_submissions(reddit, database, limit=100):
	changes_made = False

	notification_submissions = database.get_submissions_with_notifications()

	rescan_date = utils.datetime_now() - timedelta(hours=24)
	total_count_rescans = database.get_count_submissions_for_rescan(rescan_date)
	rescan_submissions = database.get_submissions_for_rescan(rescan_date, max(limit - len(notification_submissions), 0))

	ids = []
	notification_dict = {}
	for submission in notification_submissions:
		notification_dict[submission.submission_id] = submission
		ids.append(f"t3_{submission.submission_id}")

	rescan_dict = {}
	for submission in rescan_submissions:
		rescan_dict[submission.submission_id] = submission
		ids.append(f"t3_{submission.submission_id}")

	deleted_ids = []
	updated_ids = []
	if len(ids):
		if len(ids) == 1:
			reddit_submissions = [reddit.get_submission(ids[0][3:])]
		else:
			reddit_submissions = reddit.call_info(ids)

		for reddit_submission in reddit_submissions:
			db_submission = None
			try:
				if reddit_submission.id in notification_dict:
					db_submission = notification_dict[reddit_submission.id]
					if reddit_submission.removed_by_category is not None:
						counters.rescan_count.labels(result="delete").inc()
						changes_made = True
						deleted_ids.append(reddit_submission.id)

						count_notifications = database.delete_notifications_for_submission(db_submission)
						log.info(f"Deleted {count_notifications} notifications for <{db_submission.url}>")

						database.delete_submission(db_submission, delete_comment=True)
					else:
						updated_ids.append(reddit_submission.id)
						counters.rescan_count.labels(result="none").inc()

				elif reddit_submission.id in rescan_dict:
					db_submission = rescan_dict[reddit_submission.id]
					changes_made = True
					if reddit_submission.removed_by_category is not None:
						counters.rescan_count.labels(result="delete").inc()
						database.delete_submission(db_submission, delete_comment=True)
						deleted_ids.append(reddit_submission.id)
					else:
						if db_submission.title is None:
							counters.rescan_count.labels(result="update").inc()
							db_submission.title = reddit_submission.title
						else:
							counters.rescan_count.labels(result="none").inc()
						updated_ids.append(reddit_submission.id)
						db_submission.rescanned = True

				else:
					log.warning(f"Got {reddit_submission.id} from rescan call, but not in either dict")

			except Exception as err:
				if utils.process_error(f"Error rescanning submission {reddit_submission.id}", err, traceback.format_exc()):
					pass
				if isinstance(err, prawcore.exceptions.Forbidden):
					log.warning(f"Got forbidding rescanning submission {reddit_submission.id}")
					deleted_ids.append(reddit_submission.id)
					if db_submission is not None:
						count_notifications = database.delete_notifications_for_submission(db_submission)
						log.info(f"Deleted {count_notifications} notifications for <{db_submission.url}>")
						database.delete_submission(db_submission, delete_comment=True)
					pass
				raise

		count_str = f"{len(notification_submissions)}/{len(rescan_submissions)}/{len(ids)}/{len(notification_submissions) + total_count_rescans}"
		if len(updated_ids) and len(deleted_ids):
			log.info(f"{count_str}: Rescans {' '.join(updated_ids)}, Deleted {' '.join(deleted_ids)}")
		elif len(updated_ids):
			log.info(f"{count_str}: Rescans {' '.join(updated_ids)}")
		elif len(deleted_ids):
			log.info(f"{count_str}: Deleted {' '.join(deleted_ids)}")
		else:
			log.warning(f"Something went wrong, requested {','.join(ids)} for rescan but didn't get any, deleting")
			for submission_id in ids:
				if submission_id[3:] in notification_dict:
					db_submission = notification_dict[submission_id[3:]]
					count_notifications = database.delete_notifications_for_submission(db_submission)
					log.warning(f"Deleted {count_notifications} notifications for <{db_submission.url}>")
				else:
					db_submission = rescan_dict[submission_id[3:]]

				counters.rescan_count.labels(result="delete").inc()
				changes_made = True
				database.delete_submission(db_submission, delete_comment=True)

	if changes_made:
		database.commit()

	return len(ids) / 100


def scan_subreddit_group(database, reddit, subreddits, submission_ids_scanned):
	subreddit_names = []
	for subreddit_name in subreddits:
		subreddit_names.append(subreddit_name)

	log.debug(f"Scanning subreddit group: {','.join(subreddit_names)}")
	submissions_subreddits = []
	count_existing = 0
	count_found = 0
	newest_datetime = utils.datetime_now() - timedelta(minutes=30)
	group_string = '+'.join(subreddit_names)
	error_string = None
	try:
		for submission in reddit.get_subreddit_submissions(group_string):
			if submission.author is None:
				log.debug(f"Submission {submission.id} has no author")
				continue
			if database.get_submission_by_id(submission.id) is None:
				if submission.subreddit.display_name not in subreddits:
					log.warning(f"Subreddit not in dict during scan: {submission.subreddit.display_name}")
					continue

				subreddit = subreddits[submission.subreddit.display_name]
				if subreddit.last_scanned is None:
					log.warning(f"r/{subreddit.name} has a scan time of none, initializing")
					subreddit.last_scanned = utils.datetime_now()
				submission_datetime = datetime.utcfromtimestamp(submission.created_utc)
				skip = False
				if submission_datetime < subreddit.last_scanned:
					if submission_datetime < subreddit.date_enabled or \
							submission_datetime + timedelta(hours=24) < subreddit.last_scanned:
						skip = True
						count_existing += 1

				if not skip:
					submissions_subreddits.append((submission, subreddit, submission_datetime))
					count_found += 1
			else:
				count_existing += 1

			if count_existing >= 10:
				log.debug("Breaking due to hitting 10 existing")
				break
			if count_found > 500 and len(subreddits) > 1:
				log.info("Found more than 500 posts in group, splitting")
				return False
	except prawcore.exceptions.Forbidden:
		error_string = "forbidden"
	except prawcore.exceptions.NotFound:
		error_string = "not found"
	except prawcore.exceptions.Redirect:
		error_string = "redirect"
	if error_string is not None:
		if len(subreddit_names) == 1:
			log.warning(f"Got {error_string} for subreddit: r/{group_string} : {get_blacklist_mute_message(group_string)}")
			return True
		else:
			log.warning(f"Got {error_string} for subreddit group, splitting: {group_string}")
			return False

	for submission, subreddit, submission_datetime in reversed(submissions_subreddits):
		submission_ids_scanned.append(submission.id)
		tag = None
		if subreddit.tag_enabled:
			tag = utils.extract_tag_from_title(submission.title)

		author = database.get_or_add_user(submission.author.name)
		db_submission = Submission(
			submission_id=submission.id,
			time_created=submission_datetime,
			author=author,
			subreddit=subreddit,
			permalink=submission.permalink,
			title=submission.title,
			tag=tag
		)
		database.add_submission(db_submission)

		blacklist_matched = False
		if subreddit.flair_blacklist is not None:
			if str(submission.link_flair_text).lower() in subreddit.get_flair_blacklist():
				log.debug(f"Submission matches flair blacklist: {submission.id}")
				blacklist_matched = True

		if not blacklist_matched:
			subscriptions = database.get_subscriptions_for_author_subreddit(author, subreddit, db_submission.tag)

			if len(subscriptions):
				log.info(f"Queuing {len(subscriptions)} for u/{author.name} in r/{subreddit.name} : {submission.id}")
				for subscription in subscriptions:
					database.add_notification(Notification(subscription, db_submission))

			if subreddit.prompt_type == SubredditPromptType.ALL or \
					(
						subreddit.prompt_type == SubredditPromptType.ALLOWED and
						author is not None and author in subreddit.prompt_users
					):
				log.info(f"Posting prompt for u/{submission.author.name} in r/{subreddit.name} : {submission.id}")
				bldr = utils.get_footer(db_submission.render_prompt())
				result_id, comment_result = reddit.reply_submission(submission, ''.join(bldr))
				# save prompt comment here

		if submission_datetime > subreddit.last_scanned:
			subreddit.last_scanned = submission_datetime
		if submission_datetime > newest_datetime:
			newest_datetime = submission_datetime

	for subreddit_name in subreddits:
		if newest_datetime > subreddits[subreddit_name].last_scanned:
			subreddits[subreddit_name].last_scanned = newest_datetime

	database.commit()
	return True


def scan_subreddits(reddit, database):
	current_group = {}
	current_group_size = 0
	single_subreddits = []
	submission_ids_scanned = []
	subreddits_scanned = 0
	groups_scanned = 0
	start_time = time.perf_counter()
	for subreddit in database.get_active_subreddits():
		if subreddit.last_scanned < utils.datetime_now() - timedelta(hours=1):
			log.info(f"r/{subreddit.name} hasn't been scanned since {subreddit.last_scanned}, splitting")
			single_subreddits.append(subreddit)
			continue

		if current_group_size + subreddit.posts_per_hour > 50:
			if current_group_size > 0:
				if scan_subreddit_group(database, reddit, current_group, submission_ids_scanned):
					subreddits_scanned += len(current_group)
					groups_scanned += 1
				else:
					single_subreddits.extend(current_group.values())
			current_group = {subreddit.name: subreddit}
			current_group_size = subreddit.posts_per_hour
		else:
			current_group[subreddit.name] = subreddit
			current_group_size += subreddit.posts_per_hour

	if current_group:
		if scan_subreddit_group(database, reddit, current_group, submission_ids_scanned):
			subreddits_scanned += len(current_group)
			groups_scanned += 1
		else:
			single_subreddits.extend(current_group.values())

	for subreddit in single_subreddits:
		scan_subreddit_group(database, reddit, {subreddit.name: subreddit}, submission_ids_scanned)
		subreddits_scanned += 1
		groups_scanned += 1

	delta_time = time.perf_counter() - start_time

	if not len(submission_ids_scanned):
		submission_ids_scanned.append("none")
	log.info(
		f"{' '.join(submission_ids_scanned)} in {subreddits_scanned} subs across {groups_scanned} groups in "
		f"{delta_time:.2f} seconds")
	counters.scan_rate.observe(round(delta_time, 2))
	counters.scan_items.inc(len(submission_ids_scanned))
