import praw
import OAuth2Util
import time
import datetime
import database


r = praw.Reddit("subsbot:gr.watchful.subsbot (by /u/Watchful1)")
o = OAuth2Util.OAuth2Util(r)
o.refresh(force=True)

ID_NUM = 0
SUBSCRIBER_NUM = 1
SUBSCRIBEDTO_NUM = 2
SUBREDDIT_NUM = 3
LASTCHECKED_NUM = 4

database.init()
subs = {}
prevSubreddit = None
for row in database.getSubscriptions():
	if row[SUBREDDIT_NUM] != prevSubreddit:
		if subs != {}:
			time = time.mktime(datetime.datetime.strptime(oldestTimestamp, "%Y-%m-%d %H:%M:%S").timetuple())
			print(time)
			for post in praw.helpers.submissions_between(r, prevSubreddit, time):
				print(post)

		subs = {}
		oldestTimestamp = row[LASTCHECKED_NUM]

	if row[SUBSCRIBEDTO_NUM] not in subs:
		subs[row[SUBSCRIBEDTO_NUM]] = {}

	subs[row[SUBSCRIBEDTO_NUM]][row[SUBSCRIBER_NUM]] = row[LASTCHECKED_NUM]

	prevSubreddit = row[SUBREDDIT_NUM]

database.close()
