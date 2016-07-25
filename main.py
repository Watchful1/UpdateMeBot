import praw
import OAuth2Util
import time
from datetime import datetime
import database
import logging
import logging.handlers
import os
import strings

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


### Main ###
log.info("Connecting to reddit")
r = praw.Reddit(user_agent=USER_AGENT, log_request=0)
o = OAuth2Util.OAuth2Util(r)
o.refresh(force=True)

database.init()

for message in r.get_unread(unset_has_mail=True, update_user=True, limit=100):
	# checks to see as some comments might be replys and non PMs
	if isinstance(message, praw.objects.Message):
		if "updateme" in message.body.lower():

			message.mark_as_read()

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
