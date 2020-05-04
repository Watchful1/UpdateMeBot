import discord_logging
import requests
from collections import defaultdict
from datetime import datetime, timedelta
import time

log = discord_logging.init_logging()

from database import Database
from classes.submission import Submission

earliest_date = datetime(2020, 4, 23)#datetime(2016, 8, 27)
url = "https://api.pushshift.io/reddit/submission/search/?limit=1000&sort=desc&subreddit={}&author={}&before={}"
previousEpoch = int(datetime.utcnow().timestamp())
endEpoch = int(earliest_date.timestamp())

new_db = Database()
new_db.session.query(Submission).delete(synchronize_session='fetch')

log.info(f"Starting submission ingest")
subreddit_authors = defaultdict(set)
for stat in new_db.get_all_stats_for_day(datetime.utcnow().date() - timedelta(days=1)):
	subreddit_authors[stat.subreddit].add(stat.author)

log.info(f"Ingesting across {len(subreddit_authors)} subreddits")
count_submissions = 0
count_authors = 0
for subreddit in subreddit_authors:
	log.info(f"Ingesting {len(subreddit_authors[subreddit])} authors in r/{subreddit.name}")
	for author in subreddit_authors[subreddit]:
		count_authors += 1
		count_submissions_for_author = 0
		breakOut = False
		while True:
			formatted_url = url.format(subreddit.name, author.name, str(previousEpoch))
			try:
				submissions = requests.get(
					formatted_url,
					headers={'User-Agent': "keyword counter"}
				).json()['data']
			except Exception as err:
				log.info(f"Errored {err} on url: {formatted_url}")
				breakOut = True
				break

			time.sleep(1)

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
		log.info(f"Done ingesting {count_submissions_for_author} submissions for u/{author.name} in r/{subreddit.name}")
		new_db.commit()

log.info(f"Done ingesting {count_submissions} submissions across {count_authors} authors")
new_db.close()
