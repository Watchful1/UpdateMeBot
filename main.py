#!/usr/bin/python3

import praw
import OAuth2Util
import time
import calendar
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
import feedparser
from shutil import copyfile
import reddit


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
	for subreddit in database.getSubscribedSubreddits():
		startTimestamp = datetime.utcnow()
		feed = feedparser.parse("https://www.reddit.com/r/" + subreddit['subreddit'] + "/new/.rss?sort=new&limit=100")

		subredditDatetime = datetime.strptime(subreddit['lastChecked'], "%Y-%m-%d %H:%M:%S")
		oldestIndex = len(feed.entries) - 1
		for i, post in enumerate(feed.entries):
			postDatetime = datetime(*post.updated_parsed[0:6])
			if postDatetime < subredditDatetime:
				oldestIndex = i - 1
				break
			if i == 99:
				log.info("Messaging owner that that we might have missed a post in /r/"+subreddit['subreddit'])
				strList = strings.possibleMissedPostMessage(postDatetime, subredditDatetime, subreddit['subreddit'])
				strList.append("\n\n*****\n\n")
				strList.append(strings.footer)
				if not reddit.sendMessage(globals.OWNER_NAME, "Missed Post", ''.join(strList)):
					log.warning("Could not send message to owner that we might have missed a post")

		if oldestIndex != -1:
			for post in feed.entries[oldestIndex::-1]:
				if 'author' not in post: continue
				postDatetime = datetime(*post.updated_parsed[0:6])
				for subscriber in database.getSubredditAuthorSubscriptions(subreddit['subreddit'], post.author[3:].lower()):
					if postDatetime >= datetime.strptime(subscriber['lastChecked'], "%Y-%m-%d %H:%M:%S"):
						log.info("Messaging /u/%s that /u/%s has posted a new thread in /r/%s:",
						         subscriber['subscriber'], post.author[3:], subreddit['subreddit'])
						strList = strings.alertMessage(post.author[3:], subreddit['subreddit'], post.link, subscriber['single'])

						strList.append("\n\n*****\n\n")
						strList.append(strings.footer)

						if reddit.sendMessage(subscriber['subscriber'], strings.messageSubject(subscriber['subscriber']), ''.join(strList)):
							database.checkRemoveSubscription(subscriber['ID'], subscriber['single'], postDatetime + timedelta(0,1))
						else:
							log.warning("Could not send message to /u/%s when sending update", subscriber['subscriber'])

		database.checkSubreddit(subreddit['subreddit'], startTimestamp)

		time.sleep(1)


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
	try:
		for message in reddit.getMessages():
			# checks to see as some comments might be replys and non PMs
			if isinstance(message, praw.objects.Message):
				replies = {'added': [], 'updated': [], 'exist': [], 'couldnotadd': [], 'removed': [], 'notremoved': [],
				           'subredditsAdded': [], 'commentsDeleted': [], 'alwaysPM': [], 'list': False}
				log.info("Parsing message from /u/"+str(message.author))
				for line in message.body.lower().splitlines():
					if line.startswith("updateme") or line.startswith("subscribeme"):
						users = re.findall('(?: /u/)(\w*)', line)
						subs = re.findall('(?: /r/)(\w*)', line)
						links = re.findall('(?:reddit.com/r/\w*/comments/)(\w*)', line)

						if len(links) != 0:
							try:
								submission = reddit.getSubmission(submission_id=links[0])
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
		return

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


	if oldestIndex == -1: return

	for comment in comments[oldestIndex::-1]:
		if comment['author'].lower() != globals.ACCOUNT_NAME.lower():
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
						strList.extend(strings.confirmationSection(replies['added']))
					elif replies['updated']:
						strList.extend(strings.updatedSubscriptionSection(replies['updated']))
					elif replies['exist']:
						strList.extend(strings.alreadySubscribedSection(replies['exist']))

				strList.append("\n\n*****\n\n")
				strList.append(strings.footer)

				log.info("Messaging confirmation for public comment to /u/%s for /u/%s in /r/%s:",comment['author'],comment['link_author'],comment['subreddit'])
				if not reddit.sendMessage(comment['author'], strings.messageSubject(comment['author']), ''.join(strList)):
					log.warning("Could not send message to /u/%s when sending confirmation for public comment", comment['author'])

		database.updateCommentSearchSeconds(searchTerm, datetime.utcfromtimestamp(comment['created_utc']) + timedelta(0,1))


def updateExistingComments():
	for thread in database.getIncorrectThreads(datetime.utcnow() - timedelta(days=globals.COMMENT_EDIT_DAYS_CUTOFF)):
		strList = []
		strList.extend(strings.confirmationComment(thread['single'], thread['subscribedTo'], thread['subreddit'], thread['threadID'], thread['currentCount']))
		strList.append("\n\n*****\n\n")
		strList.append(strings.footer)

		if reddit.editComment(thread['commentID'], ''.join(strList)):
			database.updateCurrentThreadCount(thread['threadID'], thread['currentCount'])
		else:
			log.warning("Could not update comment with ID %s/%s", thread['threadID'], thread['commentID'])


def deleteLowKarmaComments():
	for comment in reddit.getUserComments(globals.ACCOUNT_NAME):
		if comment.score <= -5:
			log.info("Deleting low score comment")
			reddit.deleteComment(comment=comment)


def backupDatabase():
	database.close()

	if not os.path.exists(globals.BACKUPFOLDER_NAME):
	    os.makedirs(globals.BACKUPFOLDER_NAME)
	copyfile(globals.DATABASE_NAME, globals.BACKUPFOLDER_NAME + "/" + datetime.utcnow().strftime("%Y-%m-%d_%H:%M") + ".db")

	database.init()


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

reddit.init(log, responseWhitelist)

database.init()

signal.signal(signal.SIGINT, signal_handler)

i = 1
while True:
	startTime = time.perf_counter()
	log.debug("Starting run")

	try:
		#searchComments(UPDATE)
		#searchComments(SUBSCRIPTION)

		#processMessages()

		#processSubreddits()

		if i % globals.COMMENT_EDIT_ITERATIONS == 0 or i == 1:
			updateExistingComments()
			deleteLowKarmaComments()

		if i % globals.BACKUP_ITERATIONS == 0:
			backupDatabase()
	except Exception as err:
		log.warning("Error in main function")
		log.warning(traceback.format_exc())
		break

	elapsedTime = time.perf_counter() - startTime
	log.debug("Run complete after: %d", int(elapsedTime))
	if elapsedTime > globals.WARNING_RUN_TIME:
		log.warning("Messaging owner that that the process took too long to run: %d", int(elapsedTime))
		noticeStrList = strings.longRunMessage(int(elapsedTime))
		noticeStrList.append("\n\n*****\n\n")
		noticeStrList.append(strings.footer)
		if not reddit.sendMessage(globals.OWNER_NAME, "Long Run", ''.join(noticeStrList)):
			log.warning("Could not send message to owner when notifying on long run")

	if once:
		break
	i += 1
	time.sleep(globals.SLEEP_TIME)


database.close()
