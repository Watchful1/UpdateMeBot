#!/usr/bin/python3

import praw
import time
from datetime import datetime
from datetime import timedelta
import database
import logging.handlers
import os
import strings
import re
import globals
import traceback
import sys
import signal
import requests
from shutil import copyfile
import reddit
import configparser


### Constants ###
## column numbers
# getSubscribedSubreddits query
SUBBED_SUBREDDIT = 0
SUBBED_LASTCHECKED = 1
## subscription types
SUBSCRIPTION = "subscribeme"
UPDATE = "updateme"


### Logging setup ###
LOG_LEVEL = logging.DEBUG
if not os.path.exists(globals.LOGFOLDER_NAME):
    os.makedirs(globals.LOGFOLDER_NAME)
LOG_FILENAME = globals.LOGFOLDER_NAME+"/"+"bot.log"
LOG_FILE_BACKUPCOUNT = 5
LOG_FILE_MAXSIZE = 1024 * 256

log = logging.getLogger("bot")
log.setLevel(LOG_LEVEL)
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
log_stderrHandler = logging.StreamHandler()
log_stderrHandler.setFormatter(log_formatter)
log.addHandler(log_stderrHandler)
if LOG_FILENAME is not None:
	log_fileHandler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=LOG_FILE_MAXSIZE, backupCount=LOG_FILE_BACKUPCOUNT)
	log_formatter_file = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
	log_fileHandler.setFormatter(log_formatter_file)
	log.addHandler(log_fileHandler)


### Functions ###

def signal_handler(signal, frame):
	log.info("Handling interupt")
	database.close()
	sys.exit(0)


def addDeniedRequest(deniedRequests):
	subreddits = set()
	for request in deniedRequests:
		subreddits.add(request['subreddit'])

	for subreddit in subreddits:
		count = database.getDeniedRequestsCount(subreddit)
		if database.checkUpdateDeniedRequestsNotice(subreddit, count):
			log.info("Messaging owner that that requests for /r/%s have hit %d", subreddit, count)
			noticeStrList = strings.subredditNoticeThresholdMessage(subreddit, count)
			noticeStrList.append("\n\n*****\n\n")
			noticeStrList.append(strings.footer)
			if not reddit.sendMessage(globals.OWNER_NAME, "Subreddit Threshold", ''.join(noticeStrList)):
				log.warning("Could not send message to owner when notifying on subreddit threshold")


def processSubreddits():
	subredditsCount = 0
	postsCount = 0
	messagesSent = 0
	for subreddit in database.getSubscribedSubreddits():
		subStartTime = time.perf_counter()
		subPostsCount = 0
		subredditsCount += 1
		startTimestamp = datetime.utcnow()
		#log.debug("Checking subreddit: "+subreddit['subreddit'])

		subredditDatetime = datetime.strptime(subreddit['lastChecked'], "%Y-%m-%d %H:%M:%S")
		submissions = []
		hitEnd = True
		for submission in reddit.getSubredditSubmissions(subreddit['subreddit']):
			submissionCreated = datetime.fromtimestamp(submission.created_utc)
			if submissionCreated < subredditDatetime:
				hitEnd = False
				break
			submissions.append({'id': submission.id
				                ,'dateCreated': submissionCreated
				                ,'author': str(submission.author)
				                ,'link': "https://www.reddit.com"+submission.permalink
			                })
			if len(submissions) % 50 == 0:
				log.info("Posts searched: "+str(len(submissions)))

		if hitEnd and len(submissions):
			log.info("Messaging owner that that we might have missed a post in /r/"+subreddit['subreddit'])
			strList = strings.possibleMissedPostMessage(submissions[len(submissions)-1]['dateCreated'], subredditDatetime, subreddit['subreddit'])
			strList.append("\n\n*****\n\n")
			strList.append(strings.footer)
			if not reddit.sendMessage(globals.OWNER_NAME, "Missed Post", ''.join(strList)):
				log.warning("Could not send message to owner that we might have missed a post")

		if len(submissions):
			for submission in submissions:
				postsCount += 1
				subPostsCount += 1
				for subscriber in database.getSubredditAuthorSubscriptions(subreddit['subreddit'], submission['author'].lower()):
					if submission['dateCreated'] >= datetime.strptime(subscriber['lastChecked'], "%Y-%m-%d %H:%M:%S"):
						messagesSent += 1
						log.info("Messaging /u/%s that /u/%s has posted a new thread in /r/%s:",
						         subscriber['subscriber'], submission['author'], subreddit['subreddit'])
						strList = strings.alertMessage(submission['author'], subreddit['subreddit'], submission['link'], subscriber['single'])

						strList.append("\n\n*****\n\n")
						strList.append(strings.footer)

						if reddit.sendMessage(subscriber['subscriber'], strings.messageSubject(subscriber['subscriber']), ''.join(strList)):
							database.checkRemoveSubscription(subscriber['ID'], subscriber['single'], submission['dateCreated'] + timedelta(0,1))
						else:
							log.warning("Could not send message to /u/%s when sending update", subscriber['subscriber'])

		database.checkSubreddit(subreddit['subreddit'], startTimestamp)

		#log.debug(str(subPostsCount)+" posts searched in: "+str(round(time.perf_counter() - subStartTime, 3)))

	return subredditsCount, postsCount, messagesSent


def addUpdateSubscription(Subscriber, SubscribedTo, Subreddit, date, single = True, replies = {}):
	data = {'subscriber': Subscriber.lower(), 'subscribedTo': SubscribedTo.lower(), 'subreddit': Subreddit.lower(), 'single': single}

	if not database.isSubredditWhitelisted(data['subreddit']):
		database.addDeniedRequest(data['subscriber'], data['subscribedTo'], data['subreddit'], date, data['single'])
		log.info("Could not add subscription for /u/"+data['subscriber']+" to /u/"+data['subscribedTo']+" in /r/"+data['subreddit']+", not whitelisted")
		replies["couldnotadd"].append(data)
		return

	result = database.addSubscription(data['subscriber'], data['subscribedTo'], data['subreddit'], date, single)
	if result:
		log.info("/u/"+data['subscriber']+" "+("updated" if single else "subscribed")+" to /u/"+data['subscribedTo']+" in /r/"+data['subreddit'])
		replies["added"].append(data)
	else:
		currentType = database.getSubscriptionType(data['subscriber'], data['subscribedTo'], data['subreddit'])
		if currentType is not single:
			database.setSubscriptionType(data['subscriber'], data['subscribedTo'], data['subreddit'], single)
			log.info("/u/"+data['subscriber']+" "+("changed from subscription to update" if single else "changed from update to subscription")+" for /u/"+data['subscribedTo']+" in /r/"+data['subreddit'])
			replies["updated"].append(data)
		else:
			log.info("/u/"+data['subscriber']+" is already "+("updated" if single else "subscribed")+" to /u/"+data['subscribedTo']+" in /r/"+data['subreddit'])
			replies["exist"].append(data)


def removeSubscription(Subscriber, SubscribedTo, Subreddit, replies = {}):
	data = {'subscriber': Subscriber.lower(), 'subscribedTo': SubscribedTo.lower(), 'subreddit': Subreddit.lower()}
	data['single'] = database.getSubscriptionType(data['subscriber'], data['subscribedTo'], data['subreddit'])
	if database.removeSubscription(data['subscriber'], data['subscribedTo'], data['subreddit']):
		log.info("/u/"+data['subscriber']+"'s removed /u/"+data['subscribedTo']+" in /r/"+data['subreddit'])
		replies["removed"].append(data)
	else:
		log.info("/u/"+data['subscriber']+"'s doesn't have a /u/"+data['subscribedTo']+" in /r/"+data['subreddit'])
		replies["notremoved"].append(data)


def processMessages():
	messagesProcessed = 0
	try:
		for message in reddit.getMessages():
			# checks to see as some comments might be replys and non PMs
			if isinstance(message, praw.models.Message):
				messagesProcessed += 1
				replies = {'added': [], 'updated': [], 'exist': [], 'couldnotadd': [], 'removed': [], 'notremoved': [],
				           'subredditsAdded': [], 'commentsDeleted': [], 'alwaysPM': [], 'blacklist': [],
				           'blacklistNot': False, 'list': False}
				log.info("Parsing message from /u/"+str(message.author))
				for line in message.body.lower().splitlines():
					if line.startswith("updateme") or line.startswith("subscribeme"):
						users = re.findall('(?: /u/)(\w*)', line)
						subs = re.findall('(?: /r/)(\w*)', line)
						links = re.findall('(?:reddit.com/r/\w*/comments/)(\w*)', line)

						if len(links) != 0:
							try:
								submission = reddit.getSubmission(links[0])
								users.append(str(submission.author))
								subs.append(str(submission.subreddit))
							except Exception as err:
								log.debug("Exception parsing link")

						if len(users) != 0 and len(subs) != 0 and not (len(users) > 1 and len(subs) > 1):
							subscriptionType = True if line.startswith("updateme") else False
							if len(users) > 1:
								for user in users:
									addUpdateSubscription(str(message.author), user, subs[0], datetime.utcfromtimestamp(message.created_utc), subscriptionType, replies)
							elif len(subs) > 1:
								for sub in subs:
									addUpdateSubscription(str(message.author), users[0], sub, datetime.utcfromtimestamp(message.created_utc), subscriptionType, replies)
							else:
								addUpdateSubscription(str(message.author), users[0], subs[0], datetime.utcfromtimestamp(message.created_utc), subscriptionType, replies)

					elif line.startswith("removeall"):
						log.info("Removing all subscriptions for /u/"+str(message.author).lower())
						replies['removed'].extend(database.getMySubscriptions(str(message.author).lower()))
						database.removeAllSubscriptions(str(message.author).lower())

					elif line.startswith("remove"):
						users = re.findall('(?:/u/)(\w*)', line)
						subs = re.findall('(?:/r/)(\w*)', line)

						if len(users) != 0 and len(subs) != 0 and not (len(users) > 1 and len(subs) > 1):
							if len(users) > 1:
								for user in users:
									removeSubscription(str(message.author), user, subs[0], replies)
							elif len(subs) > 1:
								for sub in subs:
									removeSubscription(str(message.author), users[0], sub, replies)
							else:
								removeSubscription(str(message.author), users[0], subs[0], replies)

					elif (line.startswith("mysubscriptions") or line.startswith("myupdates")) and not replies['list']:
						log.info("Listing subscriptions for /u/"+str(message.author).lower())
						replies['list'] = True

					elif line.startswith("deletecomment"):
						threadID = re.findall('(?: t3_)(\w*)', line)

						if len(threadID) == 0: continue

						commentID = database.deleteComment(threadID[0], str(message.author).lower())
						if commentID:
							log.info("Deleting comment with ID %s/%s", threadID[0], commentID)
							if reddit.deleteComment(id=commentID):
								replies['commentsDeleted'].append(threadID[0])
							else:
								log.warning("Could not delete comment with ID %s/%s", threadID[0], commentID)

					elif line.startswith("addsubreddit") and str(message.author).lower() == globals.OWNER_NAME.lower():
						subs = re.findall('(?:/r/)(\w*)', line)
						for sub in subs:
							log.info("Whitelisting subreddit /r/"+sub)
							deniedRequests = database.getDeniedSubscriptions(sub.lower())

							for user in deniedRequests:
								log.info("Messaging /u/%s that their subscriptions in /r/%s have been activated", user, sub)
								strList = strings.activatingSubredditMessage(sub.lower(), deniedRequests[user])
								strList.append("\n\n*****\n\n")
								strList.append(strings.footer)
								if not reddit.sendMessage(user, strings.messageSubject(user), ''.join(strList)):
									log.warning("Could not send message to /u/%s when activating subreddit", user)
							replies['subredditsAdded'].append({'subreddit': sub, 'subscribers': len(deniedRequests)})

							database.activateSubreddit(sub)

					elif line.startswith("subredditpm") and str(message.author).lower() == globals.OWNER_NAME.lower():
						subs = re.findall('(?:/r/)(\w*)', line)
						if line.startswith("subredditpmtrue"):
							alwaysPM = True
						elif line.startswith("subredditpmfalse"):
							alwaysPM = False
						else:
							continue

						for sub in subs:
							log.info("Setting subreddit /r/"+sub+" to "+("don't " if not alwaysPM else "")+"alwaysPM")
							database.setAlwaysPMForSubreddit(sub.lower(), alwaysPM)
							replies['alwaysPM'].append({'subreddit': sub, 'alwaysPM': alwaysPM})

					elif line.startswith("leavemealone") or line.startswith("talktome"):
						addBlacklist = True if line.startswith("leavemealone") else False
						subs = re.findall('(?:/r/)(\w*)', line)
						users = re.findall('(?:/u/)(\w*)', line)

						if len(subs) or len(users):
							if str(message.author).lower() == globals.OWNER_NAME.lower():
								for sub in subs:
									log.info(("Blacklisting" if addBlacklist else "Removing blacklist for")+" subreddit /r/"+sub)
									result = database.blacklist(sub, True, addBlacklist)
									replies['blacklist'].append({'name': sub, 'isSubreddit': True, 'added': addBlacklist, 'result': result})

								for user in users:
									log.info(("Blacklisting" if addBlacklist else "Removing blacklist for")+" user /u/"+user)
									result = database.blacklist(user, False, addBlacklist)
									replies['blacklist'].append({'name': user, 'isSubreddit': False, 'added': addBlacklist, 'result': result})
							else:
								log.info("User /u/"+str(message.author).lower()+"tried tried to blacklist")
								replies['blacklistNot'] = True
						else:
							username = str(message.author).lower()
							log.info(("Blacklisting" if addBlacklist else "Removing blacklist for")+" user /u/"+username)
							result = database.blacklist(username, False, addBlacklist)
							replies['blacklist'].append({'name': username, 'isSubreddit': False, 'added': addBlacklist, 'result': result})

				reddit.markMessageRead(message)

				strList = []
				sectionCount = 0

				if replies['added']:
					sectionCount += 1
					strList.extend(strings.confirmationSection(replies['added']))
					strList.append("\n\n*****\n\n")
				if replies['updated']:
					sectionCount += 1
					strList.extend(strings.updatedSubscriptionSection(replies['updated']))
					strList.append("\n\n*****\n\n")
				if replies['exist']:
					sectionCount += 1
					strList.extend(strings.alreadySubscribedSection(replies['exist']))
					strList.append("\n\n*****\n\n")
				if replies['removed']:
					sectionCount += 1
					strList.extend(strings.removeUpdatesConfirmationSection(replies['removed']))
					strList.append("\n\n*****\n\n")
				if replies['commentsDeleted']:
					sectionCount += 1
					strList.extend(strings.deletedCommentSection(replies['commentsDeleted']))
					strList.append("\n\n*****\n\n")
				if replies['list']:
					sectionCount += 1
					strList.extend(strings.yourUpdatesSection(database.getMySubscriptions(str(message.author).lower())))
					strList.append("\n\n*****\n\n")
				if replies['couldnotadd']:
					sectionCount += 1
					strList.extend(strings.couldNotSubscribeSection(replies['couldnotadd']))
					strList.append("\n\n*****\n\n")

					addDeniedRequest(replies['couldnotadd'])
				if replies['subredditsAdded']:
					sectionCount += 1
					strList.extend(strings.subredditActivatedMessage(replies['subredditsAdded']))
					strList.append("\n\n*****\n\n")
				if replies['alwaysPM']:
					sectionCount += 1
					strList.extend(strings.subredditAlwaysPMMessage(replies['alwaysPM']))
					strList.append("\n\n*****\n\n")
				if replies['blacklist']:
					sectionCount += 1
					strList.extend(strings.blacklistSection(replies['blacklist']))
					strList.append("\n\n*****\n\n")
				if replies['blacklistNot']:
					sectionCount += 1
					strList.extend(strings.blacklistNotSection())
					strList.append("\n\n*****\n\n")

				if sectionCount == 0:
					log.info("Nothing found in message")
					strList.append(strings.couldNotUnderstandSection)
					strList.append("\n\n*****\n\n")

				strList.append(strings.footer)

				log.debug("Sending message to /u/"+str(message.author))
				if not reddit.replyMessage(message, ''.join(strList)):
					log.warning("Exception sending confirmation message")
	except Exception as err:
		log.warning("Exception reading messages")
		log.warning(traceback.format_exc())

	return messagesProcessed


def searchComments(searchTerm):
	if searchTerm == UPDATE:
		subscriptionType = True
	elif searchTerm == SUBSCRIPTION:
		subscriptionType = False

	try:
		comments = requests.get("https://api.pushshift.io/reddit/search?q="+searchTerm+"&limit=100",
	                       headers={'User-Agent': globals.USER_AGENT}).json()['data']
	except Exception as err:
		log.warning("Could not parse data for search term: "+searchTerm)
		return 0, 0

	timestamp = database.getCommentSearchTime(searchTerm)
	if timestamp is None:
		timestamp = START_TIME
		database.updateCommentSearchSeconds(searchTerm, timestamp)

	# we want to start at the oldest. Since we update the current timestamp at each item,
	# if we crash, we don't want to lose anything
	oldestIndex = len(comments) - 1
	for i, comment in enumerate(comments):
		if datetime.utcfromtimestamp(comment['created_utc']) < timestamp:
			oldestIndex = i - 1
			break
		if i == 99:
			log.info("Messaging owner that that we might have missed a comment")
			strList = strings.possibleMissedCommentMessage(datetime.utcfromtimestamp(comment['created_utc']), timestamp)
			strList.append("\n\n*****\n\n")
			strList.append(strings.footer)
			if not reddit.sendMessage(globals.OWNER_NAME, "Missed Comment", ''.join(strList)):
				log.warning("Could not send message to owner that we might have missed a comment")


	if oldestIndex == -1:
		return 0, 0

	commentsAdded = 0
	commentsSearched = 0
	for comment in comments[oldestIndex::-1]:
		if comment['author'].lower() != globals.ACCOUNT_NAME.lower():
			commentsSearched += 1

			if database.isBlacklisted(comment['author'].lower(), comment['subreddit'].lower()):
				log.info("Skipping comment by /u/"+comment['author']+" in /r/"+comment['subreddit']+", blacklisted")
				continue

			log.info("Found public comment by /u/"+comment['author'])
			replies = {'added': [], 'updated': [], 'exist': [], 'couldnotadd': []}
			addUpdateSubscription(comment['author'], comment['link_author'], comment['subreddit'],
					datetime.utcfromtimestamp(comment['created_utc']), subscriptionType, replies)

			posted = False
			if len(replies['couldnotadd']) == 0 and not database.alwaysPMForSubreddit(comment['subreddit']) and not database.isThreadReplied(comment['link_id'][3:]):
				strList = []
				existingSubscribers = database.getAuthorSubscribersCount(comment['subreddit'].lower(), comment['link_author'].lower())
				strList.extend(strings.confirmationComment(subscriptionType, comment['link_author'], comment['subreddit'], comment['link_id'][3:], existingSubscribers))
				strList.append("\n\n*****\n\n")
				strList.append(strings.footer)

				log.info("Publicly replying to /u/%s for /u/%s in /r/%s:",comment['author'],comment['link_author'],comment['subreddit'])
				resultCommentID = reddit.replyComment(comment['id'], ''.join(strList))
				if resultCommentID is not None:
					database.addThread(comment['link_id'][3:], resultCommentID, comment['link_author'].lower(), comment['subreddit'].lower(),
				                comment['author'].lower(), datetime.utcfromtimestamp(comment['created_utc']), existingSubscribers, subscriptionType)
					posted = True
				else:
					log.warning("Could not publicly reply to /u/%s", comment['author'])

			if not posted:
				strList = []
				if len(replies['couldnotadd']) >= 1:
					addDeniedRequest(replies['couldnotadd'])
					strList.extend(strings.couldNotSubscribeSection(replies['couldnotadd']))
				else:
					if replies['added']:
						commentsAdded += 1
						strList.extend(strings.confirmationSection(replies['added']))
					elif replies['updated']:
						commentsAdded += 1
						strList.extend(strings.updatedSubscriptionSection(replies['updated']))
					elif replies['exist']:
						strList.extend(strings.alreadySubscribedSection(replies['exist']))

				strList.append("\n\n*****\n\n")
				strList.append(strings.footer)

				log.info("Messaging confirmation for public comment to /u/%s for /u/%s in /r/%s:",comment['author'],comment['link_author'],comment['subreddit'])
				if not reddit.sendMessage(comment['author'], strings.messageSubject(comment['author']), ''.join(strList)):
					log.warning("Could not send message to /u/%s when sending confirmation for public comment", comment['author'])

		database.updateCommentSearchSeconds(searchTerm, datetime.utcfromtimestamp(comment['created_utc']) + timedelta(0,1))

	return commentsSearched, commentsAdded


def updateExistingComments():
	commentsUpdated = 0
	for thread in database.getIncorrectThreads(datetime.utcnow() - timedelta(days=globals.COMMENT_EDIT_DAYS_CUTOFF)):
		commentsUpdated += 1
		strList = []
		strList.extend(strings.confirmationComment(thread['single'], thread['subscribedTo'], thread['subreddit'], thread['threadID'], thread['currentCount']))
		strList.append("\n\n*****\n\n")
		strList.append(strings.footer)

		if reddit.editComment(thread['commentID'], ''.join(strList)):
			database.updateCurrentThreadCount(thread['threadID'], thread['currentCount'])
		else:
			log.warning("Could not update comment with ID %s/%s", thread['threadID'], thread['commentID'])

	return commentsUpdated


def deleteLowKarmaComments():
	commentsDeleted = 0
	for comment in reddit.getUserComments(globals.ACCOUNT_NAME):
		if comment.score <= -5:
			commentsDeleted += 1
			log.info("Deleting low score comment")
			reddit.deleteComment(comment=comment)

	return commentsDeleted


def backupDatabase():
	database.close()

	if not os.path.exists(globals.BACKUPFOLDER_NAME):
	    os.makedirs(globals.BACKUPFOLDER_NAME)
	copyfile(globals.DATABASE_NAME, globals.BACKUPFOLDER_NAME + "/" + datetime.utcnow().strftime("%Y-%m-%d_%H:%M") + ".db")

	database.init()

lastMark = None
def markTime(name, startTime = None):
	global lastMark
	global timings
	if startTime == None:
		timings[name] = time.perf_counter() - lastMark
		lastMark = time.perf_counter()
		return lastMark
	else:
		timings[name] = time.perf_counter() - startTime
		return time.perf_counter()


### Main ###
log.debug("Connecting to reddit")

START_TIME = datetime.utcnow()

once = False
responseWhitelist = None
for arg in sys.argv:
	# don't loop
	if arg == "-once":
		once = True

	# if it's just -debug don't send any messages. If it's -debug=test1,test2 only send messages to those users
	if arg.startswith("-debug"):
		responseWhitelist = []
		if arg.startswith("-debug="):
			responseWhitelist = arg[7:].split(',')

config = configparser.ConfigParser()
config.read('oauth.ini')

client_id = config['credentials']['client_id']
client_secret = config['credentials']['client_secret']
refresh_token = config['credentials']['refresh_token']
reddit.init(log, responseWhitelist, client_id, client_secret, refresh_token)

database.init()

signal.signal(signal.SIGINT, signal_handler)

i = 1
while True:
	log.debug("Starting run")

	timings = {}
	counts = {}
	lastMark = time.perf_counter()
	startTime = markTime('start')

	try:
		counts['updateCommentsSearched'], counts['updateCommentsAdded'] = searchComments(UPDATE)
		markTime('SearchCommentsUpdate')

		counts['subCommentsSearched'], counts['subCommentsAdded'] = searchComments(SUBSCRIPTION)
		markTime('SearchCommentsSubscribe')

		counts['messagesProcessed'] = processMessages()
		markTime('ProcessMessages')

		counts['subredditsCount'], counts['postsCount'], counts['subscriptionMessagesSent'] = processSubreddits()
		markTime('ProcessSubreddits')

		if i % globals.COMMENT_EDIT_ITERATIONS == 0 or i == 1:
			counts['existingCommentsUpdated'] = updateExistingComments()
			markTime('UpdateExistingComments')

			counts['lowKarmaCommentsDeleted'] = deleteLowKarmaComments()
			markTime('DeleteLowKarmaComments')

		if i % globals.BACKUP_ITERATIONS == 0:
			backupDatabase()
			markTime('BackupDatabase')
	except Exception as err:
		log.warning("Error in main function")
		log.warning(traceback.format_exc())
		break

	markTime('end', startTime)
	logStrList = strings.longRunLog(timings, counts)
	log.debug(''.join(logStrList))

	if timings['end'] > globals.WARNING_RUN_TIME:
		log.warning("Messaging owner that that the process took too long to run: %d", int(timings['end']))
		noticeStrList = strings.longRunMessage(timings, counts)

		noticeStrList.append("\n\n*****\n\n")
		noticeStrList.append(strings.footer)
		if not reddit.sendMessage(globals.OWNER_NAME, "Long Run", ''.join(noticeStrList)):
			log.warning("Could not send message to owner when notifying on long run")

	if once:
		break
	i += 1
	time.sleep(globals.SLEEP_TIME)


database.close()
