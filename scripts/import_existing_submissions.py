import discord_logging
import requests
from collections import defaultdict
from datetime import datetime, timedelta

log = discord_logging.init_logging()

from database import Database
from classes.submission import Submission

earliest_date = datetime(2016, 8, 27)
url = "https://api.pushshift.io/reddit/submission/search/?limit=1000&sort=desc&subreddit={}&author={}&before={}"
previousEpoch = int(datetime.utcnow().timestamp())
endEpoch = int(earliest_date.timestamp())

new_db = Database()
new_db.session.query(Submission).delete(synchronize_session='fetch')

log.info(f"Starting submission ingest")
subreddit_authors = defaultdict(set)
for subscription in new_db.get_all_subscriptions():
	if subscription.subreddit.is_enabled:
		subreddit_authors[subscription.subreddit].add(subscription.author)

log.info(f"Ingesting across {len(subreddit_authors)} subreddits")
count_submissions = 0
count_authors = 0
for subreddit in subreddit_authors:
	log.info(f"Ingesting r/{subreddit.name}")
	for author in subreddit_authors[subreddit]:
		log.info(f"Ingesting u/{author.name} in r/{subreddit.name}")
		count_authors += 1
		count_submissions_for_author = 0
		breakOut = False
		while True:
			submissions = requests.get(
				url.format(subreddit.name, author.name, str(previousEpoch)),
				headers={'User-Agent': "keyword counter"}
			).json()['data']
			if len(submissions) == 0:
				break
			for submission in submissions:
				previousEpoch = submission['created_utc'] - 1
				submission_created = datetime.utcfromtimestamp(submission['created_utc'])

				stat = new_db.get_stat_for_author_subreddit_day(
					date=submission_created.date(),
					author=author,
					subreddit=subreddit
				)
				if stat is None:
					breakOut = True
					break

				new_db.add_submission(
					Submission(
						submission_id=submission['id'],
						time_created=submission_created,
						author=author,
						subreddit=subreddit,
						permalink=submission['permalink'],
						messages_sent=stat.count_subscriptions
					)
				)
				count_submissions += 1
				count_submissions_for_author += 1

				if previousEpoch < endEpoch:
					breakOut = True
					break
			if breakOut:
				break
		log.info(f"Done ingesting {count_submissions_for_author} submissions")
		new_db.commit()

log.info(f"Done ingesting {count_submissions} submissions across {count_authors} authors")
new_db.close()
