from src import database
from src import strings
import logging.handlers

log = logging.getLogger("bot")

def addUpdateSubscription(Subscriber, SubscribedTo, Subreddit, date, single = True, filter = None, replies = {}):
	data = {'subscriber': Subscriber.lower(), 'subscribedTo': SubscribedTo.lower(), 'subreddit': Subreddit.lower(), 'single': single}

	if not database.isSubredditWhitelisted(data['subreddit']):
		database.addDeniedRequest(data['subscriber'], data['subscribedTo'], data['subreddit'], date, data['single'])
		log.info("Could not add subscription for /u/"+data['subscriber']+" to /u/"+data['subscribedTo']+" in /r/"+data['subreddit']+", not whitelisted")
		replies["couldnotadd"].append(data)
		return

	result = database.addSubscription(data['subscriber'], data['subscribedTo'], data['subreddit'], date, single, filter)
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
	if database.removeSubscription(data['subscriber'], data['subscribedTo'], data['subreddit']):
		log.info("/u/"+data['subscriber']+"'s removed /u/"+data['subscribedTo']+" in /r/"+data['subreddit'])
		replies["removed"].append(data)
	else:
		log.info("/u/"+data['subscriber']+"'s doesn't have a /u/"+data['subscribedTo']+" in /r/"+data['subreddit'])
		replies["notremoved"].append(data)


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


def passesFilter(submission, filter):
	if filter == "none": return True
	log.debug("Filter: "+filter)
	for filStr in filter.split(','):
		if filStr.startswith('-'):
			require = False
		elif filStr.startswith('+'):
			require = True
		else:
			log.debug("Bad filter, skipping: "+filStr)
			continue

		if filStr.find('=') == -1:
			fil = filStr[1:].lower()
			value = None
		else:
			fil = filStr[1:filStr.find('=')].lower()
			value = filStr[filStr.find('=')+1:].lower()

		matches = False
		if fil == "flair":
			log.debug("Comparing flair: "+str(submission.link_flair_text).lower()+" : "+value)
			if str(submission.link_flair_text).lower() == value: matches = True

		if (matches and not require) or (not matches and require):
			log.debug("Matched filter, returning false")
			return False

	return True