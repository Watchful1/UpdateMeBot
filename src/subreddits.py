import logging.handlers
import traceback
from datetime import datetime
from datetime import timedelta

import database
import globals
import reddit
import strings
import utility

log = logging.getLogger("bot")


submissionIds = set()


def processSubreddits():
	subredditsCount = 0
	groupsCount = 0
	postsCount = 0
	messagesSent = 0
	foundPosts = []
	for subreddits in database.getSubscribedSubreddits():
		groupsCount += 1
		subPostsCount = 0
		startTimestamp = datetime.utcnow()
		earliestDatetime = datetime.utcnow()
		subredditsStrings = []

		for subreddit in subreddits:
			subredditsStrings.append(subreddit['subreddit'])
			subredditDatetime = datetime.strptime(subreddit['lastChecked'], "%Y-%m-%d %H:%M:%S")
			if earliestDatetime - subredditDatetime > timedelta(seconds=0):
				earliestDatetime = subredditDatetime

			subredditsCount += 1

		subredditString = '+'.join(subredditsStrings)
		#log.debug("Searching subreddit group: "+subredditString)

		submissions = []
		hitEnd = True
		try:
			for submission in reddit.getSubredditSubmissions(subredditString):
				submissionCreated = datetime.utcfromtimestamp(submission.created_utc)
				if submissionCreated < earliestDatetime:
					hitEnd = False
					break
				if submissionCreated > startTimestamp:
					log.debug("Found newer timestamp than start: {} : {}".format(submissionCreated, startTimestamp))
					# startTimestamp = submissionCreated
				if submission.id in submissionIds:
					log.debug("Found duplicate submission: {} : {} : {}".format(submission.id, submissionCreated, earliestDatetime))
				else:
					submissionIds.add(submission.id)
				if len(submissionIds) > 5000:
					log.debug("Purging submissionIds")
					submissionIds.clear()
				submissions.append({'id': submission.id, 'dateCreated': submissionCreated, 'author': str(submission.author).lower(),
									'link': "https://www.reddit.com"+submission.permalink, 'submission': submission,
									'subreddit': str(submission.subreddit).lower()})
				if len(submissions) % 50 == 0:
					log.info("Posts searched in "+str(submission.subreddit)+": "+str(len(submissions)))
		except Exception as err:
			log.debug("Could not fetch subreddits: "+subredditString)
			log.warning(traceback.format_exc())
			continue

		if hitEnd and len(submissions):
			log.info("Messaging owner that that we might have missed a post in /r/"+subredditString)
			strList = strings.possibleMissedPostMessage(submissions[len(submissions) - 1]['dateCreated'], earliestDatetime,
			                                            subredditString)
			strList.append("\n\n*****\n\n")
			strList.append(strings.footer)
			if not reddit.sendMessage(globals.OWNER_NAME, "Missed Post", ''.join(strList)):
				log.warning("Could not send message to owner that we might have missed a post")

		if len(submissions):
			for submission in submissions:
				postsCount += 1
				subPostsCount += 1
				foundPosts.append(submission['id'])

				passesSubFilter = utility.passesFilter(submission['submission'], database.getFilter(submission['subreddit']))

				if database.isPrompt(submission['author'], submission['subreddit']) and passesSubFilter and \
						not database.isThreadReplied(submission['id']):
					log.info("Posting a prompt for /u/"+submission['author']+" in /r/"+submission['subreddit'])
					subredditDefaultSubscribe = database.subredditDefaultSubscribe(submission['subreddit'])
					promptStrList = strings.promptPublicComment(submission['author'], submission['subreddit'])
					promptStrList.append("\n\n*****\n\n")
					promptStrList.append(strings.footer)
					resultCommentID = reddit.replySubmission(submission['id'], ''.join(promptStrList))
					if resultCommentID is not None:
						database.addThread(submission['id'], resultCommentID, submission['author'], submission['subreddit'],
						                   "", datetime.utcnow(), 0, subredditDefaultSubscribe, True)

				for subscriber in database.getSubredditAuthorSubscriptions(submission['subreddit'], submission['author']):
					if submission['dateCreated'] > datetime.strptime(subscriber['lastChecked'], "%Y-%m-%d %H:%M:%S"):
						if (subscriber['filter'] != "none" and utility.passesFilter(submission, subscriber['filter'])) or \
								(subscriber['filter'] == "none" and passesSubFilter):
							messagesSent += 1
							log.info("Messaging /u/%s that /u/%s has posted a new thread in /r/%s: %s",
							         subscriber['subscriber'], submission['author'], submission['subreddit'], submission['id'])
							strList = strings.alertMessage(submission['author'], submission['subreddit'], submission['link'],
							                               subscriber['single'])

							strList.append("\n\n*****\n\n")
							strList.append(strings.footer)

							if reddit.sendMessage(subscriber['subscriber'], strings.messageSubject(subscriber['subscriber']),
							                      ''.join(strList)):
								database.checkRemoveSubscription(subscriber['ID'], subscriber['single'], submission['dateCreated']
								                                 + timedelta(0,1))
							else:
								log.warning("Could not send message to /u/%s when sending update", subscriber['subscriber'])

		for subreddit in subreddits:
			database.checkSubreddit(subreddit['subreddit'], startTimestamp)

		#log.debug(str(subPostsCount)+" posts searched in: "+str(round(time.perf_counter() - subStartTime, 3)))

	return subredditsCount, groupsCount, postsCount, messagesSent, foundPosts
