import discord_logging
import math
import traceback
from datetime import datetime
from datetime import timedelta

log = discord_logging.get_logger()

import utils


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
			log.debug(f"Profiled subreddit {subreddit.name} from {subreddit.post_per_hour} to {posts_per_hour}")
			subreddit.post_per_hour = posts_per_hour
			subreddit.last_profiled = utils.datetime_now()
			changes_made = True
		except Exception as err:
			log.warning(f"Error profiling subreddit: {subreddit.name}")
			log.warning(traceback.format_exc())

	if changes_made:
		database.commit()


def scan_subreddit_group(database, reddit, subreddits):
	posts = []
	for post in reddit.get_subreddit_submissions(subreddits):


	return True


def scan_subreddits(database, reddit):
	current_group = []
	current_group_size = 0
	single_subreddits = []
	for subreddit in database.get_active_subreddits():
		if subreddit.last_scanned < utils.datetime_now() - timedelta(hours=1):
			single_subreddits.append(subreddit)
			continue

		if current_group_size + subreddit.post_per_hour > 50:
			if current_group_size > 0:
				if not scan_subreddit_group(database, reddit, current_group):
					single_subreddits.extend(current_group)
			current_group = [subreddit]
			current_group_size = subreddit.post_per_hour
		else:
			current_group.append(subreddit)
			current_group_size += subreddit.post_per_hour

	if not scan_subreddit_group(database, reddit, current_group):
		single_subreddits.extend(current_group)

	for subreddit in single_subreddits:
		scan_subreddit_group(database, reddit, [subreddit])
