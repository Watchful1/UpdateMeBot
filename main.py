import praw
import OAuth2Util
import time
import datetime
import database
import logging
import logging.handlers
import os

### Global variables ###
USER_AGENT = "subsbot:gr.watchful.subsbot (by /u/Watchful1)"


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


### Main ###
log.info("Connecting to reddit")
r = praw.Reddit(USER_AGENT)
o = OAuth2Util.OAuth2Util(r)
o.refresh(force=True)

database.init()
subs = {}
prevSubreddit = None
for row in database.getSubscriptions():
	if row[SUBREDDIT_NUM] != prevSubreddit:
		if subs != {}:
			oldestSeconds = time.mktime(datetime.datetime.strptime(oldestTimestamp, "%Y-%m-%d %H:%M:%S").timetuple())
			log.info("Getting posts in %s newer than %s",prevSubreddit,oldestTimestamp)
			for post in praw.helpers.submissions_between(r, prevSubreddit, oldestSeconds):
				print(post)

		subs = {}
		oldestTimestamp = row[LASTCHECKED_NUM]

	if row[SUBSCRIBEDTO_NUM] not in subs:
		subs[row[SUBSCRIBEDTO_NUM]] = {}

	subs[row[SUBSCRIBEDTO_NUM]][row[SUBSCRIBER_NUM]] = row[LASTCHECKED_NUM]

	prevSubreddit = row[SUBREDDIT_NUM]

database.close()
