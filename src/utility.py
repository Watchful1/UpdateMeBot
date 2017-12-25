import logging.handlers

import database
import globals
import reddit
import strings

log = logging.getLogger("bot")


def combineDictLists(dictA, dictB):
	if dictB is not None:
		for key in dictB:
			if type(dictB[key]) is list:
				dictA[key].extend(dictB[key])
			else:
				dictA[key] = dictB[key]


def addUpdateSubscription(Subscriber, SubscribedTo, Subreddit, date, single=True, filter=None):
	data = {'subscriber': Subscriber.lower(), 'subscribedTo': SubscribedTo.lower(), 'subreddit': Subreddit.lower(),
	        'single': single}

	if not database.isSubredditWhitelisted(data['subreddit']):
		database.addDeniedRequest(data['subscriber'], data['subscribedTo'], data['subreddit'], date, data['single'])
		log.info("Could not add subscription for /u/" + data['subscriber'] + " to /u/" + data['subscribedTo'] + " in /r/" +
			data['subreddit'] + ", not whitelisted")
		return "couldnotadd", data

	result = database.addSubscription(data['subscriber'], data['subscribedTo'], data['subreddit'], date, single, filter)
	if result:
		log.info("/u/" + data['subscriber'] + " " + ("updated" if single else "subscribed") + " to /u/" + data[
			'subscribedTo'] + " in /r/" + data['subreddit'])
		return "added", data
	else:
		currentType = database.getSubscriptionType(data['subscriber'], data['subscribedTo'], data['subreddit'])
		if currentType is not single:
			database.setSubscriptionType(data['subscriber'], data['subscribedTo'], data['subreddit'], single)
			log.info("/u/" + data['subscriber'] + " " +
			         ("changed from subscription to update" if single else "changed from update to subscription") +
			         " for /u/" + data['subscribedTo'] + " in /r/" + data['subreddit'])
			return "updated", data
		else:
			log.info("/u/" + data['subscriber'] + " is already " + ("updated" if single else "subscribed") + " to /u/" +
			         data['subscribedTo'] + " in /r/" + data['subreddit'])
			return "exist", data


def removeSubscription(Subscriber, SubscribedTo, Subreddit, replies={}):
	data = {'subscriber': Subscriber.lower(), 'subscribedTo': SubscribedTo.lower(), 'subreddit': Subreddit.lower()}
	if database.removeSubscription(data['subscriber'], data['subscribedTo'], data['subreddit']):
		log.info("/u/" + data['subscriber'] + "'s removed /u/" + data['subscribedTo'] + " in /r/" + data['subreddit'])
		return "removed", data
	else:
		log.info(
			"/u/" + data['subscriber'] + "'s doesn't have a /u/" + data['subscribedTo'] + " in /r/" + data['subreddit'])
		return "notremoved", data


def checkDeniedRequests(subreddit):
	count = database.getDeniedRequestsCount(subreddit)
	if database.checkUpdateDeniedRequestsNotice(subreddit, count):
		log.info("Messaging owner that that requests for /r/%s have hit %d", subreddit, count)
		noticeStrList = strings.subredditNoticeThresholdMessage(subreddit, count)
		noticeStrList.append("\n\n*****\n\n")
		noticeStrList.append(strings.footer)
		if not reddit.sendMessage(globals.OWNER_NAME, "Subreddit Threshold", ''.join(noticeStrList)):
			log.warning("Could not send message to owner when notifying on subreddit threshold")


def passesFilter(submission, filter):
	if filter == "none": return True
	#log.debug("Filter: " + filter)
	for filStr in filter.split(','):
		if filStr.startswith('-'):
			require = False
		elif filStr.startswith('+'):
			require = True
		else:
			log.debug("Bad filter, skipping: " + filStr)
			continue

		if filStr.find('=') == -1:
			fil = filStr[1:].lower()
			value = None
		else:
			fil = filStr[1:filStr.find('=')].lower()
			value = filStr[filStr.find('=') + 1:].lower()

		matches = False
		if fil == "flair":
			#log.debug("Comparing flair: " + str(submission.link_flair_text).lower() + " : " + value)
			if str(submission.link_flair_text).lower() == value: matches = True

		if (matches and not require) or (not matches and require):
			#log.debug("Matched filter: " + filter)
			return False

	#log.debug("Passed filter: " + filter)
	return True
