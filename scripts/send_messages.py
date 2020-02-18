import sqlite3
import praw
from datetime import datetime
from datetime import timedelta

r = praw.Reddit("Watchful1", user_agent="script agent")

dbConn = sqlite3.connect("database.db")
c = dbConn.cursor()
for row in c.execute('''
		select SubscribedTo, Subreddit, count(*) as subscribers
		from subscriptions
		group by SubscribedTo, Subreddit
		order by subscribers desc
		'''):
	user = row[0]
	subreddit = row[1]
	subscribers = row[2]
	if subscribers > 1000:
		found = False
		try:
			for submission in r.redditor(user).submissions.new(limit=100):
				if submission.stickied or submission.pinned:
					continue
				if datetime.utcfromtimestamp(submission.created_utc) < datetime.utcnow() - timedelta(days=200):
					break
				if submission.subreddit.display_name == subreddit:
					found = True
					break
		except Exception:
			continue

		if found:
			print(f"u/{user} r/{subreddit} : {subscribers} ---------------")
		else:
			print(f"u/{user} r/{subreddit} : {subscribers}")

dbConn.close()
