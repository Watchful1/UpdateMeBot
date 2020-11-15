import discord_logging
from datetime import datetime

log = discord_logging.init_logging()

from praw_wrapper import Reddit
from database import Database

reddit = Reddit("Watchful1BotTest", True)

database = Database()

#database.engine.execute("alter table submissions add column title VARCHAR(300)")

submissions = {}
submission_ids = []
count_title = 0
count_deleted = 0
count_total = database.get_count_all_submissions()
for submission in database.get_all_submissions():
	submissions[submission.submission_id] = submission
	submission_ids.append(f"t3_{submission.submission_id}")

log.info(f"{count_title} + {count_deleted} = {count_title + count_deleted} / {count_total}")
for reddit_submission in reddit.reddit.info(fullnames=submission_ids):
	db_submission = submissions[reddit_submission.id]
	if reddit_submission.removed_by_category is not None:
		database.delete_submission(db_submission)
		count_deleted += 1
	else:
		db_submission.title = reddit_submission.title
		count_title += 1

	if (count_title + count_deleted) % 1000 == 0:
		log.info(f"{count_title} + {count_deleted} = {count_title + count_deleted} / {count_total}")
		database.commit()

log.info(f"{count_title} + {count_deleted} = {count_title + count_deleted} / {count_total}")
database.commit()
database.close()
