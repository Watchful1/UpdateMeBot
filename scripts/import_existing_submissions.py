import discord_logging
import requests
from collections import defaultdict
from datetime import datetime, timedelta
import time

log = discord_logging.init_logging()

from database import Database
from classes.submission import Submission

earliest_nosleep_date = datetime(2017, 11, 1)

earliest_date = datetime(2016, 8, 27)
subreddit_author_url = "https://api.pushshift.io/reddit/submission/search/?limit=1000&sort=desc&subreddit={}&author={}&before={}"
subreddit_url = "https://api.pushshift.io/reddit/submission/search/?limit=1000&sort=desc&subreddit={}&before={}"
nowEpoch = int(datetime(2020, 5, 9, 21, 52, 36).timestamp())
endEpoch = int(earliest_date.timestamp())

new_db = Database()
new_db.session.query(Submission).delete(synchronize_session='fetch')

log.info(f"Starting submission ingest")
subreddit_authors = defaultdict(dict)
for stat in new_db.get_all_stats_for_day(datetime.utcnow().date() - timedelta(days=2)):
	subreddit_authors[stat.subreddit][stat.author.name] = stat.author

log.info(f"Ingesting across {len(subreddit_authors)} subreddits")
count_submissions = 0
count_authors = 0
for subreddit in subreddit_authors:
	if subreddit.name in ['nosleep', 'HFY']:
		log.info(f"Ingesting r/{subreddit.name} by date")
		authors = subreddit_authors[subreddit]
		breakOut = False
		previousEpoch = nowEpoch
		count_submissions_for_sub = 0
		while True:
			formatted_url = subreddit_url.format(subreddit.name, str(previousEpoch))
			log.debug(formatted_url)
			try:
				submissions = requests.get(formatted_url, headers={'User-Agent': "u/watchful1"}).json()['data']
			except Exception as err:
				log.info(f"Errored {err} on url: {formatted_url}")
				break

			if len(submissions) == 0:
				log.debug("Breaking on no submissions")
				break
			submission_created = None
			for submission in submissions:
				previousEpoch = submission['created_utc'] - 1

				if previousEpoch < endEpoch:
					log.debug("Breaking on before end date")
					breakOut = True
					break

				submission_created = datetime.utcfromtimestamp(submission['created_utc'])

				if subreddit.name == 'nosleep' and submission_created < earliest_nosleep_date:
					breakOut = True
					break

				author = authors.get(submission['author'])
				if author is not None:
					stat = new_db.get_stat_for_author_subreddit_day(
						date=submission_created.date(),
						author=author,
						subreddit=subreddit
					)
					if stat is None:
						continue

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
					count_submissions_for_sub += 1

			log.info(f"{submission_created.strftime('%Y-%m-%d')} : {count_submissions_for_sub}")
			if breakOut:
				break
		log.info(f"Done ingesting {count_submissions_for_sub} submissions for for r/{subreddit.name}")

	else:
		log.info(f"Ingesting {len(subreddit_authors[subreddit])} authors in r/{subreddit.name}")
		for author_name in subreddit_authors[subreddit]:
			count_authors += 1
			count_submissions_for_author = 0
			breakOut = False
			previousEpoch = nowEpoch
			while True:
				formatted_url = subreddit_author_url.format(subreddit.name, author_name, str(previousEpoch))
				log.debug(formatted_url)
				try:
					submissions = requests.get(formatted_url, headers={'User-Agent': "u/watchful1"}).json()['data']
				except Exception as err:
					log.info(f"Errored {err} on url: {formatted_url}")
					break

				time.sleep(1)

				if len(submissions) == 0:
					log.debug("Breaking on no submissions")
					break
				for submission in submissions:
					previousEpoch = submission['created_utc'] - 1

					if previousEpoch < endEpoch:
						breakOut = True
						log.debug("Breaking on before end date")
						break

					submission_created = datetime.utcfromtimestamp(submission['created_utc'])

					stat = new_db.get_stat_for_author_subreddit_day(
						date=submission_created.date(),
						author=subreddit_authors[subreddit][author_name],
						subreddit=subreddit
					)
					if stat is None:
						breakOut = True
						log.debug("Breaking on no stats")
						break

					new_db.add_submission(
						Submission(
							submission_id=submission['id'],
							time_created=submission_created,
							author=subreddit_authors[subreddit][author_name],
							subreddit=subreddit,
							permalink=submission['permalink'],
							messages_sent=stat.count_subscriptions
						)
					)
					count_submissions += 1
					count_submissions_for_author += 1
				if breakOut:
					break
			log.info(f"Done ingesting {count_submissions_for_author} submissions for u/{author_name} in r/{subreddit.name}")
		new_db.commit()

log.info(f"Done ingesting {count_submissions} submissions across {count_authors} authors")
new_db.close()
