#!/usr/bin/python3

import logging.handlers
import os
import signal
import sys
import time
import traceback
from datetime import datetime
from shutil import copyfile

from . import comments
from src import database
from src import globals
from src import messages
from src import reddit
from src import strings
from src import subreddits

### Logging setup ###
LOG_LEVEL = logging.DEBUG
if not os.path.exists(globals.LOGFOLDER_NAME):
	os.makedirs(globals.LOGFOLDER_NAME)
LOG_FILENAME = globals.LOGFOLDER_NAME + "/" + "bot.log"
LOG_FILE_BACKUP_COUNT = 5
LOG_FILE_MAXSIZE = 1024 * 256 * 16

log = logging.getLogger("bot")
log.setLevel(LOG_LEVEL)
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
log_stderrHandler = logging.StreamHandler()
log_stderrHandler.setFormatter(log_formatter)
log.addHandler(log_stderrHandler)
if LOG_FILENAME is not None:
	log_fileHandler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=LOG_FILE_MAXSIZE,
	                                                       backupCount=LOG_FILE_BACKUP_COUNT)
	log_formatter_file = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
	log_fileHandler.setFormatter(log_formatter_file)
	log.addHandler(log_fileHandler)


### Functions ###

def signal_handler(signal, frame):
	log.info("Handling interrupt")
	database.close()
	sys.exit(0)


def backupDatabase():
	database.close()

	if not os.path.exists(globals.BACKUPFOLDER_NAME):
		os.makedirs(globals.BACKUPFOLDER_NAME)
	copyfile(globals.DATABASE_NAME,
	         globals.BACKUPFOLDER_NAME + "/" + datetime.utcnow().strftime("%Y-%m-%d_%H:%M") + ".db")

	database.init()


def markTime(name, start=None):
	global lastMark
	global timings
	if start is None:
		timings[name] = time.perf_counter() - lastMark
		lastMark = time.perf_counter()
		return lastMark
	else:
		timings[name] = time.perf_counter() - start
		return time.perf_counter()


### Main ###
log.debug("Connecting to reddit")

APP_START_TIME = datetime.utcnow()

once = False
noSearchComments = False
noSearchPosts = False
noRespondMessages = False
responseWhitelist = None
user = None
if len(sys.argv) >= 2:
	user = sys.argv[1]
	for arg in sys.argv:
		if arg == 'once':
			once = True
		elif arg.startswith("debug="):
			responseWhitelist = []
			if arg.startswith("debug="):
				responseWhitelist = arg[6:].split(',')
		elif arg == "noSearchComments":
			noSearchComments = True
			log.debug("Comment searching disabled")
		elif arg == "noSearchPosts":
			noSearchPosts = True
			log.debug("Post searching disabled")
		elif arg == "noRespondMessages":
			noRespondMessages = True
			log.debug("Message responses disabled")
else:
	log.error("No user specified, aborting")
	sys.exit(0)

if not reddit.init(log, responseWhitelist, user):
	sys.exit(0)

database.init()

signal.signal(signal.SIGINT, signal_handler)

errors = []
i = 1
while True:
	log.debug("Starting run")

	errors = []

	timings = {
		'end': 0,
		'SearchCommentsUpdate': 0,
		'SearchCommentsSubscribe': 0,
		'ProcessMessages': 0,
		'ProcessSubreddits': 0
	}
	counts = {
		'updateCommentsSearched': 0,
		'updateCommentsAdded': 0,
		'subCommentsSearched': 0,
		'subCommentsAdded': 0,
		'messagesProcessed': 0,
		'subredditsCount': 0,
		'postsCount': 0,
		'subscriptionMessagesSent': 0,
		'existingCommentsUpdated': 0,
		'lowKarmaCommentsDeleted': 0
	}
	lastMark = time.perf_counter()
	startTime = markTime('start')

	updateRequestSeconds = 0
	subscribeRequestSeconds = 0
	try:
		if not noSearchComments:
			counts['updateCommentsSearched'], counts['updateCommentsAdded'], updateRequestSeconds, newErrors = \
				comments.searchComments(globals.UPDATE_NAME, APP_START_TIME)
			errors.append(newErrors)
			markTime('SearchCommentsUpdate')

			time.sleep(1)

			counts['subCommentsSearched'], counts['subCommentsAdded'], subscribeRequestSeconds, newErrors = \
				comments.searchComments(globals.SUBSCRIPTION_NAME, APP_START_TIME)
			errors.append(newErrors)
			markTime('SearchCommentsSubscribe')

		if not noRespondMessages:
			counts['messagesProcessed'] = messages.processMessages()
			markTime('ProcessMessages')

		if not noSearchPosts:
			counts['subredditsCount'], counts['postsCount'], counts[
				'subscriptionMessagesSent'] = subreddits.processSubreddits()
			markTime('ProcessSubreddits')

		if i % globals.COMMENT_EDIT_ITERATIONS == 0 or i == 1:
			counts['existingCommentsUpdated'] = comments.updateExistingComments()
			markTime('UpdateExistingComments')

			counts['lowKarmaCommentsDeleted'] = comments.deleteLowKarmaComments()
			markTime('DeleteLowKarmaComments')

		if i % globals.BACKUP_ITERATIONS == 0:
			backupDatabase()
			markTime('BackupDatabase')
	except Exception as err:
		log.warning("Error in main function")
		log.warning(traceback.format_exc())

		seconds = 150
		recovered = False
		for num in range(1, 4):
			time.sleep(seconds)
			if reddit.checkConnection():
				recovered = True
				break
			seconds = seconds * 2

		problemStrList = []
		if recovered:
			log.warning("Messaging owner that that we recovered from a problem")
			problemStrList.append("Recovered from an exception after " + str(seconds) + " seconds.")
			problemStrList.append("\n\n*****\n\n")
			problemStrList.append(strings.footer)
			if not reddit.sendMessage(globals.OWNER_NAME, "Recovered", ''.join(problemStrList)):
				log.warning("Could not send message to owner when notifying recovery")
		else:
			log.warning("Messaging owner that that we failed to recover from a problem")
			problemStrList.append("Failed to recovered from an exception after " + str(seconds) + " seconds.")
			problemStrList.append("\n\n*****\n\n")
			problemStrList.append(strings.footer)
			if not reddit.sendMessage(globals.OWNER_NAME, "Failed recovery", ''.join(problemStrList)):
				log.warning("Could not send message to owner when notifying failed recovery")
			break

	markTime('end', startTime)
	try:
		logStrList = strings.longRunLog(timings, counts)
		log.debug(''.join(logStrList))
	except Exception as err:
		log.debug("Could not build long run log")
		log.warning(traceback.format_exc())

	if timings['end'] > (globals.WARNING_RUN_TIME + counts['subscriptionMessagesSent'] + counts['updateCommentsAdded'] +
				counts['subCommentsAdded'] + counts['existingCommentsUpdated'] + updateRequestSeconds +
				subscribeRequestSeconds) or len(errors):
		log.debug("updateRequestSeconds: " + str(updateRequestSeconds) + " subscribeRequestSeconds: " +
		        str(subscribeRequestSeconds))
		log.warning("Messaging owner that that the process took too long to run or we encountered errors: %d",
		            int(timings['end']))
		noticeStrList = strings.longRunMessage(timings, counts, errors)

		noticeStrList.append("\n\n*****\n\n")
		noticeStrList.append(strings.footer)
		if not reddit.sendMessage(globals.OWNER_NAME, "Long Run", ''.join(noticeStrList)):
			log.warning("Could not send message to owner when notifying on long run")

	if once:
		break
	i += 1
	time.sleep(globals.SLEEP_TIME)

database.close()
