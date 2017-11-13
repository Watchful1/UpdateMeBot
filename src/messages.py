from src import reddit
from src import database
from src import strings
from src import utility
from src import globals
import praw
import re
from datetime import datetime
import traceback
import logging.handlers

log = logging.getLogger("bot")


def processMessages():
	messagesProcessed = 0
	try:
		for message in reddit.getMessages():
			# checks to see as some comments might be replys and non PMs
			if isinstance(message, praw.models.Message):
				messagesProcessed += 1
				replies = {'added': [], 'updated': [], 'exist': [], 'couldnotadd': [], 'removed': [], 'notremoved': [],
				           'subredditsAdded': [], 'commentsDeleted': [], 'alwaysPM': [], 'blacklist': [], 'prompt': [],
				           'blacklistNot': False, 'list': False}
				msgAuthor = str(message.author).lower()
				log.info("Parsing message from /u/"+msgAuthor)
				for line in message.body.lower().splitlines():
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
									utility.addUpdateSubscription(str(message.author), user, subs[0],
									                              datetime.utcfromtimestamp(message.created_utc),
									                              subscriptionTypeSingle, filter, replies)
							elif len(subs) > 1:
								for sub in subs:
									utility.addUpdateSubscription(str(message.author), users[0], sub,
									                              datetime.utcfromtimestamp(message.created_utc),
									                              subscriptionTypeSingle, filter, replies)
							else:
								utility.addUpdateSubscription(str(message.author), users[0], subs[0],
								                              datetime.utcfromtimestamp(message.created_utc),
								                              subscriptionTypeSingle, filter, replies)

					elif line.startswith("removeall"):
						log.info("Removing all subscriptions for /u/"+msgAuthor)
						replies['removed'].extend(database.getMySubscriptions(msgAuthor))
						database.removeAllSubscriptions(msgAuthor)

					elif line.startswith("remove"):
						users = re.findall('(?:/u/)([\w-]*)', line)
						subs = re.findall('(?:/r/)(\w*)', line)

						if len(users) != 0 and len(subs) != 0 and not (len(users) > 1 and len(subs) > 1):
							if len(users) > 1:
								for user in users:
									utility.removeSubscription(str(message.author), user, subs[0], replies)
							elif len(subs) > 1:
								for sub in subs:
									utility.removeSubscription(str(message.author), users[0], sub, replies)
							else:
								utility.removeSubscription(str(message.author), users[0], subs[0], replies)

					elif (line.startswith("mysubscriptions") or line.startswith("myupdates")) and not replies['list']:
						log.info("Listing subscriptions for /u/"+msgAuthor)
						replies['list'] = True

					elif line.startswith("deletecomment"):
						threadID = re.findall('(?: t3_)(\w*)', line)

						if len(threadID) == 0: continue

						commentID = database.deleteComment(threadID[0], msgAuthor)
						if commentID:
							log.info("Deleting comment with ID %s/%s", threadID[0], commentID)
							if reddit.deleteComment(id=commentID):
								replies['commentsDeleted'].append(threadID[0])
							else:
								log.warning("Could not delete comment with ID %s/%s", threadID[0], commentID)

					elif line.startswith("addsubreddit") and msgAuthor == globals.OWNER_NAME.lower():
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
							replies['subredditsAdded'].append({'subreddit': sub, 'subscribers': len(deniedRequests)})

							database.activateSubreddit(sub, line.startswith("addsubredditsub"), filter)

					elif line.startswith("subredditpm") and msgAuthor == globals.OWNER_NAME.lower():
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
						users = re.findall('(?:/u/)([\w-]*)', line)

						if len(subs) or len(users):
							if msgAuthor == globals.OWNER_NAME.lower():
								for sub in subs:
									log.info(("Blacklisting" if addBlacklist else "Removing blacklist for")+" subreddit /r/"+sub)
									result = database.blacklist(sub, True, addBlacklist)
									replies['blacklist'].append({'name': sub, 'isSubreddit': True, 'added': addBlacklist, 'result': result})

								for user in users:
									log.info(("Blacklisting" if addBlacklist else "Removing blacklist for")+" user /u/"+user)
									result = database.blacklist(user, False, addBlacklist)
									replies['blacklist'].append({'name': user, 'isSubreddit': False, 'added': addBlacklist, 'result': result})
							else:
								log.info("User /u/"+msgAuthor+" tried to blacklist")
								replies['blacklistNot'] = True
						else:
							log.info(("Blacklisting" if addBlacklist else "Removing blacklist for")+" user /u/"+msgAuthor)
							result = database.blacklist(msgAuthor, False, addBlacklist)
							replies['blacklist'].append({'name': msgAuthor, 'isSubreddit': False, 'added': addBlacklist, 'result': result})

					elif line.startswith("prompt") or line.startswith("dontprompt"):
						addPrompt = True if line.startswith("prompt") else False
						subs = re.findall('(?:/r/)(\w*)', line)
						users = re.findall('(?:/u/)([\w-]*)', line)

						skip = False
						if len(subs) and len(users) and msgAuthor == globals.OWNER_NAME.lower():
							sub = subs[0].lower()
							user = users[0].lower()
						elif len(subs):
							sub = subs[0].lower()
							user = msgAuthor
						else:
							skip = True

						if not skip and not database.isSubredditWhitelisted(sub):
							log.info("Could not add prompt for /u/"+user+" in /r/"+sub+", not whitelisted")
							replies["couldnotadd"].append({'subreddit': sub})
							skip = True

						if not skip:
							if database.isPrompt(user, sub):
								if not addPrompt:
									log.info("Removing prompt for /u/"+user+" in /r/"+sub)
									database.removePrompt(user, sub)
									replies['prompt'].append({'name': user, 'subreddit': sub, 'added': False, 'exists': False})
								else:
									log.info("Prompt doesn't exist for /u/"+user+" in /r/"+sub)
									replies['prompt'].append({'name': user, 'subreddit': sub, 'added': False, 'exists': True})
							else:
								if addPrompt:
									log.info("Adding prompt for /u/"+user+" in /r/"+sub)
									database.addPrompt(user, sub)
									replies['prompt'].append({'name': user, 'subreddit': sub, 'added': True, 'exists': False})
								else:
									log.info("Prompt already exists for /u/"+user+" in /r/"+sub)
									replies['prompt'].append({'name': user, 'subreddit': sub, 'added': False, 'exists': True})

				reddit.markMessageRead(message)

				strList = []
				sectionCount = 0

				if len(replies['added']):
					sectionCount += 1
					strList.extend(strings.confirmationSection(replies['added']))
					strList.append("\n\n*****\n\n")
				if len(replies['updated']):
					sectionCount += 1
					strList.extend(strings.updatedSubscriptionSection(replies['updated']))
					strList.append("\n\n*****\n\n")
				if len(replies['exist']):
					sectionCount += 1
					strList.extend(strings.alreadySubscribedSection(replies['exist']))
					strList.append("\n\n*****\n\n")
				if len(replies['removed']):
					sectionCount += 1
					strList.extend(strings.removeUpdatesConfirmationSection(replies['removed']))
					strList.append("\n\n*****\n\n")
				if len(replies['commentsDeleted']):
					sectionCount += 1
					strList.extend(strings.deletedCommentSection(replies['commentsDeleted']))
					strList.append("\n\n*****\n\n")
				if replies['list']:
					sectionCount += 1
					strList.extend(strings.yourUpdatesSection(database.getMySubscriptions(msgAuthor)))
					strList.append("\n\n*****\n\n")
				if len(replies['couldnotadd']):
					sectionCount += 1
					strList.extend(strings.couldNotSubscribeSection(replies['couldnotadd']))
					strList.append("\n\n*****\n\n")

					utility.addDeniedRequest(replies['couldnotadd'])
				if len(replies['subredditsAdded']):
					sectionCount += 1
					strList.extend(strings.subredditActivatedMessage(replies['subredditsAdded']))
					strList.append("\n\n*****\n\n")
				if len(replies['alwaysPM']):
					sectionCount += 1
					strList.extend(strings.subredditAlwaysPMMessage(replies['alwaysPM']))
					strList.append("\n\n*****\n\n")
				if len(replies['blacklist']):
					sectionCount += 1
					strList.extend(strings.blacklistSection(replies['blacklist']))
					strList.append("\n\n*****\n\n")
				if replies['blacklistNot']:
					sectionCount += 1
					strList.extend(strings.blacklistNotSection())
					strList.append("\n\n*****\n\n")
				if len(replies['prompt']):
					sectionCount += 1
					strList.extend(strings.promptSection(replies['prompt']))
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
