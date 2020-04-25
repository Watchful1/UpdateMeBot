import discord_logging
import math
import traceback
import time
from datetime import datetime
from datetime import timedelta

log = discord_logging.get_logger()

import utils
from classes.submission import Submission
from classes.notification import Notification
from classes.comment import DbComment
from classes.enums import SubredditPromptType, ReturnType


def subreddit_posts_per_hour(reddit, subreddit_name):
	count = 0
	oldest_submission = utils.datetime_now()
	for submission in reddit.get_subreddit_submissions(subreddit_name):
		count += 1
		submission_created = datetime.utcfromtimestamp(submission.created_utc)
		if submission_created < oldest_submission:
			oldest_submission = submission_created
		if count >= 50:
			break

	if count == 0:
		return 1

	hours = math.trunc((utils.datetime_now() - oldest_submission).total_seconds() / (60 * 60))
	if hours == 0:
		posts_per_hour = count
	else:
		posts_per_hour = int(math.ceil(count / hours))

	return posts_per_hour


def profile_subreddits(database, reddit):
	changes_made = False
	for subreddit in database.get_unprofiled_subreddits():
		try:
			posts_per_hour = subreddit_posts_per_hour(reddit, subreddit.name)
			log.info(f"Profiled subreddit {subreddit.name} from {subreddit.post_per_hour} to {posts_per_hour}")
			subreddit.post_per_hour = posts_per_hour
			subreddit.last_profiled = utils.datetime_now()
			changes_made = True
		except Exception as err:
			log.warning(f"Error profiling subreddit: {subreddit.name}")
			log.warning(traceback.format_exc())

	if changes_made:
		database.commit()


def scan_subreddit_group(database, reddit, subreddits, submission_ids_scanned):
	subreddit_names = []
	for subreddit_name in subreddits:
		subreddit_names.append(subreddit_name)

	submissions = []
	count_existing = 0
	count_found = 0
	for submission in reddit.get_subreddit_submissions('+'.join(subreddit_names)):
		if database.get_submission_by_id(submission.id) is None:
			submissions.append(submission)
			count_found += 1
		else:
			count_existing += 1

		if count_existing > 10:
			break
		if count_found > 500 and len(subreddits) > 1:
			log.info("Found more than 500 posts in group, splitting")
			return False

	for submission in reversed(submissions):
		if submission.subreddit.display_name not in subreddits:
			log.warning(f"Subreddit not in dict during scan: {submission.subreddit.display_name}")
			continue

		subreddit = subreddits[submission.subreddit.display_name]
		submission_datetime = datetime.utcfromtimestamp(submission.created_utc)
		if submission_datetime < subreddit.last_scanned:
			log.warning(f"Submission before last scanned: {submission.url}")

		submission_ids_scanned.append(submission.id)
		db_submission = Submission(
			submission_id=submission.id,
			time_created=submission_datetime,
			author_name=submission.author.name,
			subreddit=subreddit,
			permalink=submission.permalink
		)
		database.add_submission(db_submission)

		blacklist_matched = False
		if subreddit.flair_blacklist is not None:
			if str(submission.link_flair_text).lower() in subreddit.get_flair_blacklist():
				log.debug(f"Submission matches flair blacklist: {submission.id}")
				blacklist_matched = True

		if not blacklist_matched:
			author = database.get_user(submission.author.name)
			if author is not None:
				subscriptions = database.get_subscriptions_for_author_subreddit(author, subreddit)

				if len(subscriptions):
					log.info(f"Queuing {len(subscriptions)} for u/{author.name} in r/{subreddit.name} : {submission.id}")
					for subscription in subscriptions:
						database.add_notification(Notification(subscription, db_submission))

			if subreddit.prompt_type == SubredditPromptType.ALL or \
					(
						subreddit.prompt_type == SubredditPromptType.ALLOWED and
						author is not None and author in subreddit.prompt_users
					):
				bldr = utils.get_footer(db_submission.render_prompt())
				result_id, comment_result = reddit.reply_submission(submission, ''.join(bldr))
				# save prompt comment here

		subreddit.last_scanned = submission_datetime

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

		if current_group_size + subreddit.post_per_hour > 50:
			if current_group_size > 0:
				if scan_subreddit_group(database, reddit, current_group, submission_ids_scanned):
					subreddits_scanned += len(current_group)
					groups_scanned += 1
				else:
					single_subreddits.extend(current_group.values())
			current_group = {subreddit.name: subreddit}
			current_group_size = subreddit.post_per_hour
		else:
			current_group[subreddit.name] = subreddit
			current_group_size += subreddit.post_per_hour

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

	log.info(
		f"{' '.join(submission_ids_scanned)} in {subreddits_scanned} subs across {groups_scanned} groups in "
		f"{delta_time:.2} seconds")
