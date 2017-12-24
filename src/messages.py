import logging.handlers
import re
import traceback
from datetime import datetime
from collections import defaultdict

import praw

import database
import globals
import reddit
import strings
import utility

log = logging.getLogger("bot")


def MessageLineUpdateSubscribe(line, author, created):
	results = defaultdict(list)
	if line.startswith("updateme") or line.startswith("subscribeme") or line.startswith("http"):
		users = re.findall('(?: /u/)([\w-]*)', line)
		subs = re.findall('(?: /r/)(\w*)', line)
		links = re.findall('(?:reddit.com/r/\w*/comments/)(\w*)', line)
		filters = re.findall('(?:filter=)(\S*)', line)

		if len(links) != 0:
			try:
				submission = reddit.getSubmission(links[0])
				users.append(str(submission.author))
				subs.append(str(submission.subreddit))
			except Exception as err:
				log.debug("Exception parsing link")

		if len(users) != 0 and len(subs) != 0 and not (len(users) > 1 and len(subs) > 1):
			if line.startswith("updateme"):
				subscriptionTypeSingle = True
			elif line.startswith("subscribeme"):
				subscriptionTypeSingle = False
			else:
				subscriptionTypeSingle = not database.subredditDefaultSubscribe(subs[0].lower())

			if len(filters):
				filter = filters[0]
			else:
				filter = None
			if len(users) > 1:
				for user in users:
					result, data = utility.addUpdateSubscription(author, user, subs[0], created, subscriptionTypeSingle, filter)
					results[result].append(data)
			elif len(subs) > 1:
				for sub in subs:
					result, data = utility.addUpdateSubscription(author, users[0], sub, created, subscriptionTypeSingle, filter)
					results[result].append(data)
			else:
				result, data = utility.addUpdateSubscription(author, users[0], subs[0], created, subscriptionTypeSingle, filter)
				results[result].append(data)

	return results


def MessageLineRemove(line, author):
	results = defaultdict(list)
	if line.startswith("removeall"):
		log.info("Removing all subscriptions for /u/"+author)
		results['removed'].append(database.getMySubscriptions(author))
		database.removeAllSubscriptions(author)

	elif line.startswith("remove"):
		users = re.findall('(?:/u/)([\w-]*)', line)
		subs = re.findall('(?:/r/)(\w*)', line)

		if len(users) != 0 and len(subs) != 0 and not (len(users) > 1 and len(subs) > 1):
			if len(users) > 1:
				for user in users:
					result, data = utility.removeSubscription(author, user, subs[0])
					results[result].append(data)
			elif len(subs) > 1:
				for sub in subs:
					result, data = utility.removeSubscription(author, users[0], sub)
					results[result].append(data)
			else:
				result, data = utility.removeSubscription(author, users[0], subs[0])
				results[result].append(data)

	return results


def MessageLineList(line, author):
	results = defaultdict(list)
	if line.startswith("mysubscriptions") or line.startswith("myupdates"):
		log.info("Listing subscriptions for /u/"+author)
		results['list'] = True

	return results


def MessageLineDelete(line, author):
	results = defaultdict(list)
	if line.startswith("deletecomment"):
		threadID = re.findall('(?: t3_)(\w*)', line)

		if len(threadID) == 0: return results

		commentID = database.deleteComment(threadID[0], author)
		if commentID:
			log.info("Deleting comment with ID %s/%s", threadID[0], commentID)
			if reddit.deleteComment(id=commentID):
				results['commentsDeleted'].append(threadID[0])
			else:
				log.warning("Could not delete comment with ID %s/%s", threadID[0], commentID)

	return results


def MessageLineAddSubreddit(line):
	results = defaultdict(list)
	if line.startswith("addsubreddit"):
		subs = re.findall('(?:/r/)(\w*)', line)
		filters = re.findall('(?:filter=)(\S*)', line)
		if len(filters):
			filter = filters[0]
			log.debug("Found filter in addsubreddit: "+filter)
		else:
			filter = None

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

			results['subredditsAdded'].append({'subreddit': sub, 'subscribers': len(deniedRequests)})

			database.activateSubreddit(sub, line.startswith("addsubredditsub"), filter)

	return results


def MessageLineSubredditPM(line):
	results = defaultdict(list)
	if line.startswith("subredditpm"):
		subs = re.findall('(?:/r/)(\w*)', line)
		if line.startswith("subredditpmtrue"):
			alwaysPM = True
		elif line.startswith("subredditpmfalse"):
			alwaysPM = False
		else:
			return results

		for sub in subs:
			log.info("Setting subreddit /r/"+sub+" to "+("don't " if not alwaysPM else "")+"alwaysPM")
			database.setAlwaysPMForSubreddit(sub.lower(), alwaysPM)
			results['alwaysPM'].append({'subreddit': sub, 'alwaysPM': alwaysPM})

	return results


def MessageLineMute(line, author, hasAdmin):
	results = defaultdict(list)
	if line.startswith("leavemealone") or line.startswith("talktome"):
		addBlacklist = True if line.startswith("leavemealone") else False
		subs = re.findall('(?:/r/)(\w*)', line)
		users = re.findall('(?:/u/)([\w-]*)', line)

		if len(subs) or len(users):
			if hasAdmin:
				for sub in subs:
					log.info(("Blacklisting" if addBlacklist else "Removing blacklist for")+" subreddit /r/"+sub)
					result = database.blacklist(sub, True, addBlacklist)
					results['blacklist'].append({'name': sub, 'isSubreddit': True, 'added': addBlacklist, 'result': result})

				for user in users:
					log.info(("Blacklisting" if addBlacklist else "Removing blacklist for")+" user /u/"+user)
					result = database.blacklist(user, False, addBlacklist)
					results['blacklist'].append({'name': user, 'isSubreddit': False, 'added': addBlacklist, 'result': result})
			else:
				log.info("User /u/"+author+" tried to blacklist")
				results['blacklistNot'] = True
		else:
			log.info(("Blacklisting" if addBlacklist else "Removing blacklist for")+" user /u/"+author)
			result = database.blacklist(author, False, addBlacklist)
			results['blacklist'].append({'name': author, 'isSubreddit': False, 'added': addBlacklist, 'result': result})

	return results


def MessageLinePrompt(line, author, hasAdmin):
	results = defaultdict(list)
	if line.startswith("prompt") or line.startswith("dontprompt"):
		addPrompt = True if line.startswith("prompt") else False
		subs = re.findall('(?:/r/)(\w*)', line)
		users = re.findall('(?:/u/)([\w-]*)', line)

		skip = False
		if len(subs) and len(users) and hasAdmin:
			sub = subs[0].lower()
			user = users[0].lower()
		elif len(subs):
			sub = subs[0].lower()
			user = author
		else:
			skip = True

		if not skip and not database.isSubredditWhitelisted(sub):
			log.info("Could not add prompt for /u/"+user+" in /r/"+sub+", not whitelisted")
			results["couldnotadd"].append({'subreddit': sub})
			skip = True
			utility.checkDeniedRequests(sub)

		if not skip:
			if database.isPrompt(user, sub):
				if not addPrompt:
					log.info("Removing prompt for /u/"+user+" in /r/"+sub)
					database.removePrompt(user, sub)
					results['prompt'].append({'name': user, 'subreddit': sub, 'added': False, 'exists': False})
				else:
					log.info("Prompt doesn't exist for /u/"+user+" in /r/"+sub)
					results['prompt'].append({'name': user, 'subreddit': sub, 'added': False, 'exists': True})
			else:
				if addPrompt:
					log.info("Adding prompt for /u/"+user+" in /r/"+sub)
					database.addPrompt(user, sub)
					results['prompt'].append({'name': user, 'subreddit': sub, 'added': True, 'exists': False})
				else:
					log.info("Prompt already exists for /u/"+user+" in /r/"+sub)
					results['prompt'].append({'name': user, 'subreddit': sub, 'added': False, 'exists': True})

	return results


def processMessages():
	messagesProcessed = 0
	try:
		for message in reddit.getMessages():
			# checks to see as some comments might be replys and non PMs
			if isinstance(message, praw.models.Message):
				messagesProcessed += 1
				replies = defaultdict(list)
				msgAuthor = str(message.author).lower()
				log.info("Parsing message from /u/"+msgAuthor)
				hasAdmin = msgAuthor == globals.OWNER_NAME.lower()

				for line in message.body.lower().splitlines():
					utility.combineDictLists(replies, MessageLineUpdateSubscribe(line, msgAuthor, datetime.utcfromtimestamp(message.created_utc)))
					utility.combineDictLists(replies, MessageLineRemove(line, msgAuthor))
					utility.combineDictLists(replies, MessageLineList(line, msgAuthor))
					utility.combineDictLists(replies, MessageLineDelete(line, msgAuthor))
					utility.combineDictLists(replies, MessageLineMute(line, msgAuthor, hasAdmin))
					utility.combineDictLists(replies, MessageLinePrompt(line, msgAuthor, hasAdmin))
					if hasAdmin:
						utility.combineDictLists(replies, MessageLineAddSubreddit(line))
						utility.combineDictLists(replies, MessageLineSubredditPM(line))


				reddit.markMessageRead(message)


				sections = [
					{'key': "added", 'function': strings.confirmationSection},
					{'key': "updated", 'function': strings.updatedSubscriptionSection},
					{'key': "exist", 'function': strings.alreadySubscribedSection},
					{'key': "removed", 'function': strings.removeUpdatesConfirmationSection},
					{'key': "commentsDeleted", 'function': strings.deletedCommentSection},
					{'key': "couldnotadd", 'function': strings.couldNotSubscribeSection},
					{'key': "subredditsAdded", 'function': strings.subredditActivatedMessage},
					{'key': "alwaysPM", 'function': strings.subredditAlwaysPMMessage},
					{'key': "blacklist", 'function': strings.blacklistSection},
					{'key': "blacklistNot", 'function': strings.blacklistNotSection},
					{'key': "prompt", 'function': strings.promptSection},
				]

				strList = []
				for section in sections:
					if section['key'] in replies:
						strList.extend(section['function'](replies['key']))
						strList.append("\n\n*****\n\n")

				# this is special cased since we need to pull in the subscriptions now, rather than during line processing
				if 'list' in replies:
					strList.extend(strings.yourUpdatesSection(database.getMySubscriptions(msgAuthor)))
					strList.append("\n\n*****\n\n")

				if len(strList) == 0:
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
