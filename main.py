import praw
import OAuth2Util
import time
from datetime import datetime
import database
import logging
import logging.handlers
import os
import strings
import re

### Global variables ###
USER_AGENT = "UpdatedMe/Subscribe (by /u/Watchful1)"


### Constants ###
# column numbers
ID_NUM = 0
SUBSCRIBER_NUM = 1
SUBSCRIBEDTO_NUM = 2
SUBREDDIT_NUM = 3
LASTCHECKED_NUM = 4


### Logging setup ###
LOG_LEVEL = logging.INFO
LOG_FOLDER = "logs"
if not os.path.exists(LOG_FOLDER):
    os.makedirs(LOG_FOLDER)
LOG_FILENAME = LOG_FOLDER+"/"+"bot.log"
LOG_FILE_BACKUPCOUNT = 5
LOG_FILE_MAXSIZE = 1024 * 256

log = logging.getLogger("bot")
log.setLevel(LOG_LEVEL)
log_formatter = logging.Formatter('%(levelname)s: %(message)s')
log_stderrHandler = logging.StreamHandler()
log_stderrHandler.setFormatter(log_formatter)
log.addHandler(log_stderrHandler)
if LOG_FILENAME is not None:
	log_fileHandler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=LOG_FILE_MAXSIZE, backupCount=LOG_FILE_BACKUPCOUNT)
	log_formatter_file = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
	log_fileHandler.setFormatter(log_formatter_file)
	log.addHandler(log_fileHandler)



### Functions ###

def searchSubreddit(subreddit, authorHash, oldestTimestamp):
	if authorHash == {}: return
	oldestSeconds = time.mktime(datetime.strptime(oldestTimestamp, "%Y-%m-%d %H:%M:%S").timetuple())
	log.info("Getting posts in %s newer than %s", subreddit, oldestTimestamp)

	# retrieving submissions takes some time, but starts with the newest first
	# so we want to cache the time we start, but don't reset the timestamps until we know we aren't going to crash
	# better to send two notifications than none
	startTimestamp = datetime.now()
	for post in praw.helpers.submissions_between(r, subreddit, oldestSeconds, verbosity=0):
		if str(post.author) in authorHash:
			for key in authorHash[str(post.author)]:
				if datetime.fromtimestamp(post.created_utc) >= datetime.strptime(authorHash[str(post.author)][key], "%Y-%m-%d %H:%M:%S"):
					log.info("Messaging /u/%s that /u/%s has posted a new thread in /r/%s",key,str(post.author),subreddit)
					r.send_message(
						recipient=key,
						subject=strings.messageSubject(key),
						message=strings.alertMessage(str(post.author),subreddit,"LINK")
					)

	database.checkSubreddit(subreddit, startTimestamp)


def addUpdateSubscription(Subscriber, SubscribedTo, Subreddit, date = datetime.now(), single = True):
	result = database.addSubsciption(Subscriber, SubscribedTo, Subreddit, date, single)
	if type(result) is tuple:
		return result
	elif result is not single:
		database.setSubscriptionType(Subscriber, SubscribedTo, Subreddit, single)
		return single
	else:
		return None



### Main ###
log.info("Connecting to reddit")
r = praw.Reddit(user_agent=USER_AGENT, log_request=0)
o = OAuth2Util.OAuth2Util(r)
o.refresh(force=True)

database.init()

for message in r.get_unread(unset_has_mail=True, update_user=True, limit=100):
	replies = {}

	# checks to see as some comments might be replys and non PMs
	if isinstance(message, praw.objects.Message):
		log.info("Parsing message from /u/"+str(message.author))
		for line in message.body.lower().splitlines():
			if line.startswith("updateme"):
				if "added" not in replies:
					replies["added"] = {}

				log.info("line: "+line)
				users = re.findall('(?:/u/)(\w*)', line)
				subs = re.findall('(?:/r/)(\w*)', line)
				links = re.findall('(?:reddit.com/r/\w*/comments/)(\w*)', line)

				if len(links) != 0:
					submission = r.get_submission(submission_id=links[0])
					log.info(str(submission.author)+" : "+str(submission.subreddit)+" : "+str(datetime.fromtimestamp(submission.created_utc)))
					result = addUpdateSubscription(str(message.author), str(submission.author), str(submission.subreddit), datetime.fromtimestamp(message.created_utc))
					if result is None:
						log.info("Subscription already exists")
					elif type(result) is bool:
						log.info("Updated subscription type to: "+str(result))
					else:
						log.info("Added subscription: "+str(result))

				elif len(users) != 0 and len(subs) != 0 and not (len(users) > 1 and len(subs) > 1):
					log.info(str(users[0])+" : "+str(subs[0]))

		# message.mark_as_read()

prevSubreddit = None
subs = {}
oldestTimestamp = None
for row in database.getSubscriptions():
	if row[SUBREDDIT_NUM] != prevSubreddit:
		searchSubreddit(prevSubreddit, subs, oldestTimestamp)
		subs = {}
		oldestTimestamp = row[LASTCHECKED_NUM]

	if row[SUBSCRIBEDTO_NUM] not in subs:
		subs[row[SUBSCRIBEDTO_NUM]] = {}

	subs[row[SUBSCRIBEDTO_NUM]][row[SUBSCRIBER_NUM]] = row[LASTCHECKED_NUM]

	prevSubreddit = row[SUBREDDIT_NUM]

searchSubreddit(prevSubreddit, subs, oldestTimestamp)

database.close()
