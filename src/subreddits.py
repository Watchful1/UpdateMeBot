from src import database
from src import reddit
from src import strings
from src import utility
from src import globals
from datetime import datetime
from datetime import timedelta
import logging.handlers

log = logging.getLogger("bot")


def processSubreddits():
	subredditsCount = 0
	postsCount = 0
	messagesSent = 0
	for subreddit in database.getSubscribedSubreddits():
		# subStartTime = time.perf_counter()
		subPostsCount = 0
		subredditsCount += 1
		startTimestamp = datetime.utcnow()
		#log.debug("Checking subreddit: "+subreddit['subreddit'])

		subredditDatetime = datetime.strptime(subreddit['lastChecked'], "%Y-%m-%d %H:%M:%S")
		submissions = []
		hitEnd = True
		for submission in reddit.getSubredditSubmissions(subreddit['subreddit']):
			submissionCreated = datetime.utcfromtimestamp(submission.created_utc)
			if submissionCreated < subredditDatetime:
				hitEnd = False
				break
			submissions.append({'id': submission.id, 'dateCreated': submissionCreated, 'author': str(submission.author),
								'link': "https://www.reddit.com"+submission.permalink, 'submission': submission})
			if len(submissions) % 50 == 0:
				log.info("Posts searched: "+str(len(submissions)))

		if hitEnd and len(submissions):
			log.info("Messaging owner that that we might have missed a post in /r/"+subreddit['subreddit'])
			strList = strings.possibleMissedPostMessage(submissions[len(submissions) - 1]['dateCreated'], subredditDatetime,
			                                            subreddit['subreddit'])
			strList.append("\n\n*****\n\n")
			strList.append(strings.footer)
			if not reddit.sendMessage(globals.OWNER_NAME, "Missed Post", ''.join(strList)):
				log.warning("Could not send message to owner that we might have missed a post")

		if len(submissions):
			for submission in submissions:
				postsCount += 1
				subPostsCount += 1

				passesSubFilter = utility.passesFilter(submission['submission'], database.getFilter(subreddit['subreddit']))

				if database.isPrompt(submission['author'].lower(), subreddit['subreddit']) and passesSubFilter:
					log.info("Posting a prompt for /u/"+submission['author'].lower()+" in /r/"+subreddit['subreddit'])
					promptStrList = strings.promptPublicComment(submission['author'].lower(), subreddit['subreddit'])
					promptStrList.append("\n\n*****\n\n")
					promptStrList.append(strings.footer)
					reddit.replySubmission(submission['id'], ''.join(promptStrList))

				for subscriber in database.getSubredditAuthorSubscriptions(subreddit['subreddit'], submission['author'].lower()):
					if submission['dateCreated'] >= datetime.strptime(subscriber['lastChecked'], "%Y-%m-%d %H:%M:%S"):
						if (subscriber['filter'] != "none" and utility.passesFilter(submission, subscriber['filter'])) or \
								(subscriber['filter'] == "none" and passesSubFilter):
							messagesSent += 1
							log.info("Messaging /u/%s that /u/%s has posted a new thread in /r/%s: %s",
							         subscriber['subscriber'], submission['author'], subreddit['subreddit'], submission['id'])
							strList = strings.alertMessage(submission['author'], subreddit['subreddit'], submission['link'],
							                               subscriber['single'])

							strList.append("\n\n*****\n\n")
							strList.append(strings.footer)

							if reddit.sendMessage(subscriber['subscriber'], strings.messageSubject(subscriber['subscriber']),
							                      ''.join(strList)):
								database.checkRemoveSubscription(subscriber['ID'], subscriber['single'], submission['dateCreated']
								                                 + timedelta(0,1))
							else:
								log.warning("Could not send message to /u/%s when sending update", subscriber['subscriber'])

		database.checkSubreddit(subreddit['subreddit'], startTimestamp)

		#log.debug(str(subPostsCount)+" posts searched in: "+str(round(time.perf_counter() - subStartTime, 3)))

	return subredditsCount, postsCount, messagesSent
