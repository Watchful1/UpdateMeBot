from src import globals
from src import database
from src import reddit
from src import strings
from src import utility
import requests
import time
from datetime import timedelta
import traceback
import logging.handlers
from datetime import datetime

log = logging.getLogger("bot")


def searchComments(searchTerm, startTime):
	global errors
	if searchTerm == globals.UPDATE_NAME:
		subscriptionType = True
	elif searchTerm == globals.SUBSCRIPTION_NAME:
		subscriptionType = False

	requestSeconds = 0
	try:
		url = "https://api.pushshift.io/reddit/comment/search?q="+searchTerm+"&limit=100&sort=desc"
		requestTime = time.perf_counter()
		json = requests.get(url, headers={'User-Agent': globals.USER_AGENT})
		requestSeconds = int(time.perf_counter() - requestTime)
		if json.status_code != 200:
			log.warning("Could not parse data for search term: "+searchTerm + " status: "+str(json.status_code))
			errors.append("Could not parse data for search term: "+str(json.status_code) + " : " +url)
			return 0, 0, 0
		comments = json.json()['data']
	except Exception as err:
		log.warning("Could not parse data for search term: "+searchTerm)
		log.warning(traceback.format_exc())
		errors.append("Could not parse data for search term: "+url)
		return 0, 0, 0

	if len(comments) == 0:
		log.warning("Could not parse data for search term, no results: "+searchTerm + " status: "+str(json.status_code))
		errors.append("Could not parse data for search term, no results: "+str(json.status_code) + " : " +url)
		return 0, 0, 0
	elif requestSeconds > 80 and len(comments) > 0:
		log.warning("Long request, but returned successfully: "+str(requestSeconds))

	timestamp = database.getCommentSearchTime(searchTerm)
	if timestamp is None:
		timestamp = startTime
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
		return 0, 0, requestSeconds

	commentsAdded = 0
	commentsSearched = 0
	for comment in comments[oldestIndex::-1]:
		if comment['author'].lower() != globals.ACCOUNT_NAME.lower():
			commentsSearched += 1

			if database.isBlacklisted(comment['author'].lower(), comment['subreddit'].lower()):
				continue

			log.info("Found public comment by /u/"+comment['author'])
			replies = {'added': [], 'updated': [], 'exist': [], 'couldnotadd': []}

			comment['link_author'] = str(reddit.getSubmission(comment['link_id'][3:]).author)

			utility.addUpdateSubscription(comment['author'], comment['link_author'], comment['subreddit'],
					datetime.utcfromtimestamp(comment['created_utc']), subscriptionType, None, replies)

			posted = False
			if len(replies['couldnotadd']) == 0 and not database.alwaysPMForSubreddit(comment['subreddit'].lower()) and not database.isThreadReplied(comment['link_id'][3:]):
				strList = []
				existingSubscribers = database.getAuthorSubscribersCount(comment['subreddit'].lower(), comment['link_author'].lower())
				strList.extend(
					strings.confirmationComment(subscriptionType, comment['link_author'], comment['subreddit'], comment['link_id'][3:], existingSubscribers))
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
					utility.addDeniedRequest(replies['couldnotadd'])
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

	return commentsSearched, commentsAdded, requestSeconds


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