#!/usr/bin/python3

import praw
import OAuth2Util
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
import feedparser
from shutil import copyfile


### Constants ###
## column numbers
# getSubscribedSubreddits query
SUBBED_SUBREDDIT = 0
SUBBED_LASTCHECKED = 1
# getSubredditAuthorSubscriptions query
SUBAUTHOR_ID = 0
SUBAUTHOR_SUBSCRIBER = 1
SUBAUTHOR_LASTCHECKED = 2
SUBAUTHOR_SINGLE = 3
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
			try:
				r.send_message(
					recipient=globals.OWNER_NAME,
					subject="Subreddit Threshold",
					message=''.join(noticeStrList)
				)
			except Exception as err:
				log.warning("Could not send message to owner when notifying on subreddit threshold")
				log.warning(traceback.format_exc())


def processSubreddits():
	for subreddit in database.getSubscribedSubreddits():
		startTimestamp = datetime.now()
		feed = feedparser.parse("https://www.reddit.com/r/" + subreddit[SUBBED_SUBREDDIT] + "/new/.rss?sort=new&limit=100")

		subredditDatetime = datetime.strptime(subreddit[SUBBED_LASTCHECKED], "%Y-%m-%d %H:%M:%S")
		oldestIndex = len(feed.entries) - 1
		for i, post in enumerate(feed.entries):
			postDatetime = datetime.fromtimestamp(time.mktime(post.updated_parsed))
			if postDatetime < subredditDatetime:
				oldestIndex = i - 1
				break
			if i == 99:
				log.info("Messaging owner that that we might have missed a post in /r/"+subreddit[SUBBED_SUBREDDIT])
				strList = strings.possibleMissedPostMessage(postDatetime, subredditDatetime, subreddit[SUBBED_SUBREDDIT])
				strList.append("\n\n*****\n\n")
				strList.append(strings.footer)
				log.debug(''.join(strList))
				try:
					r.send_message(
						recipient=globals.OWNER_NAME,
						subject="Missed Post",
						message=''.join(strList)
					)
				except Exception as err:
					log.warning("Could not send message to owner that we might have missed a post")
					log.warning(traceback.format_exc())

		if oldestIndex != -1:
			for post in feed.entries[oldestIndex::-1]:
				postDatetime = datetime.fromtimestamp(time.mktime(post.updated_parsed))
				for subscriber in database.getSubredditAuthorSubscriptions(subreddit[SUBBED_SUBREDDIT], post.author[3:].lower()):
					if postDatetime >= datetime.strptime(subscriber[SUBAUTHOR_LASTCHECKED], "%Y-%m-%d %H:%M:%S"):
						log.info("Messaging /u/%s that /u/%s has posted a new thread in /r/%s:",
						         subscriber[SUBAUTHOR_SUBSCRIBER], post.author[3:], subreddit[SUBBED_SUBREDDIT])
						strList = strings.alertMessage(post.author[3:], subreddit[SUBBED_SUBREDDIT], post.link, subscriber[SUBAUTHOR_SINGLE])

						strList.append("\n\n*****\n\n")
						strList.append(strings.footer)

						try:
							r.send_message(
								recipient=subscriber[SUBAUTHOR_SUBSCRIBER],
								subject=strings.messageSubject(subscriber[SUBAUTHOR_SUBSCRIBER]),
								message=''.join(strList)
							)
							database.checkRemoveSubscription(subscriber[SUBAUTHOR_ID], subscriber[SUBAUTHOR_SINGLE], postDatetime + timedelta(0,1))
						except Exception as err:
							log.warning("Could not send message to /u/%s when sending update", subscriber[SUBAUTHOR_SUBSCRIBER])
							log.warning(traceback.format_exc())

		database.checkSubreddit(subreddit[SUBBED_SUBREDDIT], startTimestamp)

		time.sleep(0.05)


def addUpdateSubscription(Subscriber, SubscribedTo, Subreddit, date = datetime.now(), single = True, replies = {}):
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
		for message in r.get_unread(unset_has_mail=True, update_user=True, limit=100):
			# checks to see as some comments might be replys and non PMs
			if isinstance(message, praw.objects.Message):
				replies = {'added': [], 'updated': [], 'exist': [], 'couldnotadd': [], 'removed': [], 'notremoved': [], 'subredditsAdded': [], 'commentsDeleted': [], 'list': False}
				log.info("Parsing message from /u/"+str(message.author))
				for line in message.body.lower().splitlines():
					if line.startswith("updateme") or line.startswith("subscribeme"):
						users = re.findall('(?: /u/)(\w*)', line)
						subs = re.findall('(?: /r/)(\w*)', line)
						links = re.findall('(?:reddit.com/r/\w*/comments/)(\w*)', line)

						if len(links) != 0:
							try:
								submission = r.get_submission(submission_id=links[0])
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
							try:
								log.info("Deleting comment with ID %s/%s", threadID[0], commentID)
								r.get_info(thing_id='t1_' + commentID).delete()
								replies['commentsDeleted'].append(threadID[0])
							except Exception as err:
								log.warning("Could not delete comment with ID %s/%s", threadID[0], commentID)
								log.warning(traceback.format_exc())


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
								try:
									r.send_message(
										recipient=user,
										subject=strings.messageSubject(user),
										message=''.join(strList)
									)
								except Exception as err:
									log.warning("Could not send message to /u/%s when activating subreddit", user)
									log.warning(traceback.format_exc())
							replies['subredditsAdded'].append({'subreddit': sub, 'subscribers': len(deniedRequests)})

							database.activateSubreddit(sub)

				message.mark_as_read()

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

				if sectionCount == 0:
					log.info("Nothing found in message")
					strList.append(strings.couldNotUnderstandSection)
					strList.append("\n\n*****\n\n")

				strList.append(strings.footer)

				log.debug("Sending message to /u/"+str(message.author))
				try:
					message.reply(''.join(strList))
				except Exception as err:
					log.warning("Exception sending confirmation message")
					log.warning(traceback.format_exc())
	except Exception as err:
		log.warning("Exception reading messages")
		log.warning(traceback.format_exc())


def searchComments(searchTerm):
	if searchTerm == UPDATE:
		subscriptionType = True
	elif searchTerm == SUBSCRIPTION:
		subscriptionType = False

	comments = requests.get("https://api.pushshift.io/reddit/search?q="+searchTerm+"&limit=100",
	                       headers={'User-Agent': globals.USER_AGENT}).json()['data']
	timestamp = database.getCommentSearchTime(searchTerm)
	if timestamp is None:
		timestamp = START_TIME

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
			log.debug(''.join(strList))
			try:
				r.send_message(
					recipient=globals.OWNER_NAME,
					subject="Missed Comment",
					message=''.join(strList)
				)
			except Exception as err:
				log.warning("Could not send message to owner that we might have missed a comment")
				log.warning(traceback.format_exc())


	if oldestIndex == -1: return

	for comment in comments[oldestIndex::-1]:
		if comment['author'].lower() != globals.ACCOUNT_NAME.lower():
			log.info("Found public comment by /u/"+comment['author'])
			replies = {'added': [], 'updated': [], 'exist': [], 'couldnotadd': []}
			addUpdateSubscription(comment['author'], comment['link_author'], comment['subreddit'],
					datetime.utcfromtimestamp(comment['created_utc']), subscriptionType, replies)

			strList = []
			usePM = True
			if len(replies['couldnotadd']) >= 1:
				addDeniedRequest(replies['couldnotadd'])
				strList.extend(strings.couldNotSubscribeSection(replies['couldnotadd']))
			elif database.isThreadReplied(comment['link_id'][3:]):
				if replies['added']:
					strList.extend(strings.confirmationSection(replies['added']))
				elif replies['updated']:
					strList.extend(strings.updatedSubscriptionSection(replies['updated']))
				elif replies['exist']:
					strList.extend(strings.alreadySubscribedSection(replies['exist']))
			else:
				usePM = False
				existingSubscribers = database.getAuthorSubscribersCount(comment['subreddit'].lower(), comment['link_author'].lower())
				strList.extend(strings.confirmationComment(subscriptionType, comment['link_author'], comment['subreddit'], comment['link_id'][3:], existingSubscribers))

			strList.append("\n\n*****\n\n")
			strList.append(strings.footer)

			if usePM:
				log.info("Messaging confirmation for public comment to /u/%s for /u/%s in /r/%s:",comment['author'],comment['link_author'],comment['subreddit'])
				try:
					r.send_message(
						recipient=comment['author'],
						subject=strings.messageSubject(comment['author']),
						message=''.join(strList)
					)
				except Exception as err:
					log.warning("Could not send message to /u/%s when sending confirmation for public comment", comment['author'])
					log.warning(traceback.format_exc())
			else:
				log.info("Publicly replying to /u/%s for /u/%s in /r/%s:",comment['author'],comment['link_author'],comment['subreddit'])
				try:
					resultComment = r.get_info(thing_id='t1_' + comment['id']).reply(''.join(strList))
					database.addThread(comment['link_id'][3:], resultComment.id, comment['link_author'].lower(), comment['subreddit'].lower(),
				                comment['author'].lower(), datetime.utcfromtimestamp(comment['created_utc']), existingSubscribers, subscriptionType)
				except Exception as err:
					log.warning("Could not publicly reply to /u/%s", comment['author'])
					log.warning(traceback.format_exc())

		database.updateCommentSearchSeconds(searchTerm, datetime.utcfromtimestamp(comment['created_utc']) + timedelta(0,1))


def updateExistingComments():
	for thread in database.getIncorrectThreads(datetime.now() - timedelta(days=globals.COMMENT_EDIT_DAYS_CUTOFF)):
		strList = []
		strList.extend(strings.confirmationComment(thread['single'], thread['subscribedTo'], thread['subreddit'], thread['threadID'], thread['currentCount']))
		strList.append("\n\n*****\n\n")
		strList.append(strings.footer)

		try:
			r.get_info(thing_id='t1_' + thread['commentID']).edit(''.join(strList))
			database.updateCurrentThreadCount(thread['threadID'], thread['currentCount'])
		except Exception as err:
			log.warning("Could not update comment with ID %s/%s", thread['threadID'], thread['commentID'])
			log.warning(traceback.format_exc())


def deleteLowKarmaComments():
	user = r.get_redditor(globals.ACCOUNT_NAME)
	for comment in user.get_comments(limit=100):
		if comment.score <= -5:
			log.info("Deleting low score comment")
			comment.delete()


def backupDatabase():
	database.close()

	if not os.path.exists(globals.BACKUPFOLDER_NAME):
	    os.makedirs(globals.BACKUPFOLDER_NAME)
	copyfile(globals.DATABASE_NAME, globals.BACKUPFOLDER_NAME + "/" + datetime.now().strftime("%Y-%m-%d_%H:%M") + ".db")

	database.init()


### Main ###
log.debug("Connecting to reddit")

START_TIME = datetime.now()

r = praw.Reddit(user_agent=globals.USER_AGENT, log_request=0)
o = OAuth2Util.OAuth2Util(r)
o.refresh(force=True)

database.init()

signal.signal(signal.SIGINT, signal_handler)

once = False
if len(sys.argv) > 1 and sys.argv[1] == 'once':
	once = True

i = 1
while True:
	startTime = time.perf_counter()
	log.debug("Starting run")

	try:
		searchComments(UPDATE)
		searchComments(SUBSCRIPTION)

		processMessages()

		processSubreddits()

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
		log.debug(''.join(noticeStrList))
		try:
			r.send_message(
				recipient=globals.OWNER_NAME,
				subject="Long Run",
				message=''.join(noticeStrList)
			)
		except Exception as err:
			log.warning("Could not send message to owner when notifying on long run")
			log.warning(traceback.format_exc())

	if once:
		break
	i += 1
	time.sleep(globals.SLEEP_TIME)


database.close()
