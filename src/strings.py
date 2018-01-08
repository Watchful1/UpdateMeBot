import globals


def messageSubject(user):
	return (
		"Hello {user}, UpdateMeBot Here!"
	).format(
		user=user
	)


def alertMessage(subscribedTo, subreddit, link, single):
	strList = [globals.ACCOUNT_NAME]
	strList.append(" here!\n\n")
	strList.append("/u/")
	strList.append(subscribedTo)
	strList.append(" has posted a new thread in /r/")
	strList.append(subreddit)
	strList.append("\n\n")
	strList.append("You can find it here:")
	strList.append("\n\n")
	strList.append(link)

	strList.append("\n\n*****\n\n")

	if single:
		strList.append("[Click here](")
		strList.append("http://np.reddit.com/message/compose/?to=")
		strList.append(globals.ACCOUNT_NAME)
		strList.append("&subject=Update&message=UpdateMe /u/")
		strList.append(subscribedTo)
		strList.append(" /r/")
		strList.append(subreddit)
		strList.append(") if you want to be updated the next time /u/")
		strList.append(subscribedTo)
		strList.append(" posts in /r/")
		strList.append(subreddit)
		strList.append("  \n")

		strList.append("[Click here](")
		strList.append("http://np.reddit.com/message/compose/?to=")
		strList.append(globals.ACCOUNT_NAME)
		strList.append("&subject=Subscribe&message=SubscribeMe /u/")
		strList.append(subscribedTo)
		strList.append(" /r/")
		strList.append(subreddit)
		strList.append(") if you want to be updated every time /u/")
		strList.append(subscribedTo)
		strList.append(" posts in /r/")
		strList.append(subreddit)

	else:
		strList.append("[Click here](")
		strList.append("http://np.reddit.com/message/compose/?to=")
		strList.append(globals.ACCOUNT_NAME)
		strList.append("&subject=Remove&message=Remove /u/")
		strList.append(subscribedTo)
		strList.append(" /r/")
		strList.append(subreddit)
		strList.append(") to remove your subscription to /u/")
		strList.append(subscribedTo)
		strList.append(" posts in /r/")
		strList.append(subreddit)
		strList.append("  ")

	return strList


def eachHelper(item, includeMessageType=True):
	strList = []
	if 'single' in item and item['single']:
		if includeMessageType:
			strList.append("UpdateMe ")
		strList.append("next")
	else:
		if includeMessageType:
			strList.append("SubscribeMe ")
		strList.append("each")
	strList.append(" time /u/")
	strList.append(item['subscribedTo'])
	strList.append(" posts in /r/")
	strList.append(item['subreddit'])

	return strList


def yourUpdatesSection(updateList):
	strList = ["Here are the people you asked me to update you on,"]

	for update in updateList:
		strList.append("  \n")
		strList.extend(eachHelper(update))

	return strList


def confirmationSection(addedList):
	strList = []
	hasSingle = False

	if len(addedList) == 1:
		strList.append("I will message you ")
		strList.extend(eachHelper(addedList[0], False))
		if addedList[0]['single']:
			hasSingle = True
	else:
		strList.append("I have added the following,")

		for added in addedList:
			strList.append("  \n")
			strList.extend(eachHelper(added))
			if added['single']:
				hasSingle = True

	if hasSingle:
		strList.extend("\n\n")
		strList.extend("If you want to be messaged every time instead of just the next time, you can ")
		if len(addedList) == 1:
			strList.extend("put SubscribeMe at the beginning of the above line")
		else:
			strList.extend("replace the UpdateMe with SubscribeMe at the beginning of each line")
		strList.extend(" and message it to me.")

	return strList


def couldNotSubscribeSection(couldNotSubscribeList):
	subreddits = set()
	for request in couldNotSubscribeList:
		subreddits.add(request['subreddit'])

	strList = []

	strList.append("Unfortunately I couldn't process your request")
	if len(subreddits) > 1:
		strList.append("'s")

	strList.append(" for ")

	i = 0
	length = len(subreddits)
	writingprompts = False
	for subreddit in subreddits:
		if subreddit.lower() == "writingprompts":
			writingprompts = True
		strList.append("/r/")
		strList.append(subreddit)
		if length != 1 and i+2 == length:
			strList.append(" or ")
		elif length != 1 and i+1 != length:
			strList.append(", ")
		i += 1

	strList.append(".\n\n")
	if writingprompts:
		strList.append("The moderators of /r/WritingPrompts have requested that this bot not be turned on in the sub. ")
		strList.append("If you think it would be useful, feel free to [message them](")
		strList.append("https://www.reddit.com/message/compose?to=%2Fr%2FWritingPrompts&subject=UpdateMeBot")
		strList.append(") and let them know.")
	else:
		strList.append("This bot works by checking every subreddit that someone is subscribed to every few minutes. ")
		strList.append("Each subreddit it checks takes several seconds, so I have to limit the number of subreddits or")
		strList.append(" the bot will get overloaded. If you think this would be a good subreddit for this bot, message /u/")
		strList.append(globals.OWNER_NAME)
		strList.append(" and he'll take a look. I've also logged your request, so if the subreddit does get added, ")
		strList.append("I'll automatically start sending your updates.")

	strList.append("\n\n")

	strList.append("Didn't mean to subscribe to anything? Click [here](")
	strList.append("http://np.reddit.com/message/compose/?to=")
	strList.append(globals.ACCOUNT_NAME)
	strList.append("&subject=Disable&message=LeaveMeAlone!")
	strList.append(") and the bot won't bother you anymore.")

	return strList


def alreadySubscribedSection(alreadyList):
	strList = []

	if len(alreadyList) == 1:
		strList.append("You had already asked me to message you ")
		strList.extend(eachHelper(alreadyList[0], False))
	else:
		strList.append("You had already asked me to message you for the following,")

		for already in alreadyList:
			strList.append("  \n")
			strList.extend(eachHelper(already))

	return strList


def updatedSubscriptionSection(updatedList):
	strList = []

	if len(updatedList) == 1:
		strList.append("I have updated the subscription type to message you ")
		strList.extend(eachHelper(updatedList[0], False))
	else:
		strList.append("I have updated the subscription types for the following,")

		for updated in updatedList:
			strList.append("  \n")
			strList.extend(eachHelper(updated))

	return strList


def removeUpdatesConfirmationSection(removedList):
	strList = ["I will no longer message when the following happens. "
			   "If you change your mind, you can copy the below section into a message to me.\n\n"]

	for removed in removedList:
		strList.append("  \n")
		strList.extend(eachHelper(removed))

	return strList


def activatingSubredditMessage(subreddit, subscriptions):
	strList = ["/r/"]
	strList.append(subreddit)
	strList.append(" has been added to this bot. Following is the list of users you requested to be subscribed to.\n\n")

	for subscription in subscriptions:
		if subscription['single']:
			strList.append("UpdateMe")
		else:
			strList.append("SubscribeMe")
		strList.append(" /u/")
		strList.append(subscription['subscribedTo'])
		strList.append("  \n")

	strList.append("\n\nNote, your subscription automatically starts at the time of your original request, ")
	strList.append("so if it's been a while you might get a flood of messages.")

	return strList


def subredditActivatedMessage(activations):
	strList = []

	for activation in activations:
		strList.append("/r/")
		strList.append(activation['subreddit'])
		strList.append(" has been activated and ")
		strList.append(str(activation['subscribers']))
		strList.append(" users have been notified.")
		strList.append("  \n")

	return strList


def deletedCommentSection(deletedComments):
	strList = []

	for deletedComment in deletedComments:
		strList.append("Comment in thread ")
		strList.append(deletedComment)
		strList.append(" deleted.")
		strList.append("  \n")

	strList.append("\n\n")
	strList.append("If this bot did something wrong or you have a suggestion, feel free to message /u/")
	strList.append(globals.OWNER_NAME)
	strList.append(".")

	return strList


def blacklistSection(blacklisted):
	strList = []

	for blacklist in blacklisted:
		strList.append("UpdateMeBot will ")
		if blacklist['added']:
			strList.append("not ")
		strList.append("interact with public comments ")
		if blacklist['isSubreddit']:
			strList.append("in subreddit /r/")
		else:
			strList.append("by user /u/")
		strList.append(blacklist['name'])
		strList.append(".")
		if not blacklist['added']:
			strList.append(" [Click here](")
			strList.append("http://np.reddit.com/message/compose/?to=")
			strList.append(globals.ACCOUNT_NAME)
			strList.append("&subject=Re-enable&message=TalkToMe! ")
			if blacklist['isSubreddit']:
				strList.append("/r/")
			else:
				strList.append("/u/")
			strList.append(blacklist['name'])
			strList.append(") to re-enable.")
		strList.append("  \n")

	return strList


def blacklistNotSection(empty):
	return "It looks like you tried to blacklist something that you didn't have access to."



def promptSection(prompts):
	strList = []

	for prompt in prompts:
		if prompt['exists']:
			strList.append("This prompt already exists, no changes.  \n")
		else:
			strList.append("UpdateMeBot will ")
			if not prompt['added']:
				strList.append("not ")
			strList.append("post a prompt asking for subscriptions whenever /u/")
			strList.append(prompt['name'])
			strList.append(" posts a new submission in /r/")
			strList.append(prompt['subreddit'])
			strList.append(".  \n")

	return strList


def promptPublicComment(user, subreddit):
	strList = []

	strList.append("[Click here](")
	strList.append("http://np.reddit.com/message/compose/?to=")
	strList.append(globals.ACCOUNT_NAME)
	strList.append("&subject=Subscribe&message=SubscribeMe! /u/")
	strList.append(user)
	strList.append(" /r/")
	strList.append(subreddit)
	strList.append(") ")
	strList.append(" to subscribe to /u/")
	strList.append(user)
	strList.append(" and receive a message every time they post.")

	return strList


def subredditNoticeThresholdMessage(subreddit, count):
	return ["/r/", subreddit, " has hit the notice threshold, which is ", str(count)]


def confirmationComment(subscriptionType, subscribeTo, subreddit, threadID, alreadySubscribed=0):
	strList = []

	strList.append("I will message you ")
	strList.extend(eachHelper({'subscribedTo': subscribeTo,'subreddit': subreddit,'single': subscriptionType}, False))
	strList.append(".\n\n")
	strList.append("[Click this link](http://np.reddit.com/message/compose/?to=")
	strList.append(globals.ACCOUNT_NAME)
	strList.append("&subject=Update&message=")
	if subscriptionType:
		strList.append("UpdateMe")
	else:
		strList.append("SubscribeMe")
	strList.append(" /u/")
	strList.append(subscribeTo)
	strList.append(" /r/")
	strList.append(subreddit)
	strList.append(") ")
	strList.append("to ")
	if alreadySubscribed > 1:
		strList.append("join ")
		strList.append(str(alreadySubscribed))
		strList.append(" others and")
	else:
		strList.append("also")
	strList.append(" be messaged. ")

	strList.append("The parent author can [delete this post]")
	strList.append("(http://np.reddit.com/message/compose/?to=")
	strList.append(globals.ACCOUNT_NAME)
	strList.append("&subject=Delete&message=DeleteComment t3_")
	strList.append(threadID)
	strList.append(")")

	return strList


def possibleMissedCommentMessage(oldestTimestamp, recordedTimestamp):
	strList = ["Comment search hit index 99 without finding oldest timestamp.\n\n"]
	strList.append("Oldest found timestamp: "+str(oldestTimestamp))
	strList.append("\n\n")
	strList.append("Recorded timestamp: "+str(recordedTimestamp))
	return strList


def possibleMissedPostMessage(oldestTimestamp, recordedTimestamp, subreddit):
	strList = ["Post search hit end of listing without finding oldest timestamp in /r/",subreddit,"\n\n"]
	strList.append("Oldest found timestamp: "+str(oldestTimestamp))
	strList.append("\n\n")
	strList.append("Recorded timestamp: "+str(recordedTimestamp))
	return strList


def subredditAlwaysPMMessage(subreddits):
	strList = []

	for subreddit in subreddits:
		strList.append("/r/")
		strList.append(subreddit['subreddit'])
		strList.append(" has been changed to ")
		if not subreddit['alwaysPM']:
			strList.append("don't ")
		strList.append("always PM.")
		strList.append("  \n")

	return strList


def longRunLog(timings, counts, foundPosts):
	logStrList = ["Run complete after: ", str(int(timings['end']))]
	if counts['updateCommentsAdded'] > 0:
		logStrList.append(" : Update comments added: ")
		logStrList.append(str(counts['updateCommentsAdded']))
	if counts['subCommentsAdded'] > 0:
		logStrList.append(" : Sub comments added: ")
		logStrList.append(str(counts['subCommentsAdded']))
	if counts['messagesProcessed'] > 0:
		logStrList.append(" : Messages processed: ")
		logStrList.append(str(counts['messagesProcessed']))
	logStrList.append(" : ")
	logStrList.append(str(counts['postsCount']))
	logStrList.append(" posts searched in ")
	logStrList.append(str(counts['subredditsCount']))
	logStrList.append(" subreddits across ")
	logStrList.append(str(counts['groupsCount']))
	logStrList.append(" groups")
	if 'subscriptionMessagesSent' in counts and counts['subscriptionMessagesSent'] > 0:
		logStrList.append(" subreddits : Sub messages sent: ")
		logStrList.append(str(counts['subscriptionMessagesSent']))
	if 'existingCommentsUpdated' in counts and counts['existingCommentsUpdated'] > 0:
		logStrList.append(" : Existing comments updated: ")
		logStrList.append(str(counts['existingCommentsUpdated']))
	if 'lowKarmaCommentsDeleted' in counts and counts['lowKarmaCommentsDeleted'] > 0:
		logStrList.append(" : Low karma comments deleted: ")
		logStrList.append(str(counts['lowKarmaCommentsDeleted']))
	if counts['subredditsProfiled'] > 0:
		logStrList.append(" : Subreddits profiled: ")
		logStrList.append(str(counts['subredditsProfiled']))
	if len(foundPosts):
		logStrList.append(" :")
		for post in foundPosts:
			logStrList.append(" ")
			logStrList.append(post)

	return logStrList


def longRunMessage(timings, counts, errors):
	strList = []

	strList.append("Loop run took too long: ")
	strList.append(str(int(timings['end'])))

	strList.append("\n\nUpdate comments searched, added and time: ")
	strList.append(str(counts['updateCommentsSearched']))
	strList.append(", ")
	strList.append(str(counts['updateCommentsAdded']))
	strList.append(", ")
	strList.append(str(round(timings['SearchCommentsUpdate'], 3)))

	strList.append("\n\nSub comments searched, added and time: ")
	strList.append(str(counts['subCommentsSearched']))
	strList.append(", ")
	strList.append(str(counts['subCommentsAdded']))
	strList.append(", ")
	strList.append(str(round(timings['SearchCommentsSubscribe'], 3)))

	strList.append("\n\nMessages processed, time: ")
	strList.append(str(counts['messagesProcessed']))
	strList.append(", ")
	strList.append(str(round(timings['ProcessMessages'], 3)))

	strList.append("\n\nSubreddits searched, groups, posts searched, messages sent, time: ")
	strList.append(str(counts['subredditsCount']))
	strList.append(", ")
	strList.append(str(counts['groupsCount']))
	strList.append(", ")
	strList.append(str(counts['postsCount']))
	strList.append(", ")
	strList.append(str(counts['subscriptionMessagesSent']))
	strList.append(", ")
	strList.append(str(round(timings['ProcessSubreddits'], 3)))

	if 'UpdateExistingComments' in timings:
		strList.append("\n\nExisting comments updated, time: ")
		strList.append(str(counts['existingCommentsUpdated']))
		strList.append(", ")
		strList.append(str(round(timings['UpdateExistingComments'], 3)))

	if 'DeleteLowKarmaComments' in timings:
		strList.append("\n\nLow karma comments deleted, time: ")
		strList.append(str(counts['lowKarmaCommentsDeleted']))
		strList.append(", ")
		strList.append(str(round(timings['DeleteLowKarmaComments'], 3)))

	if 'ProfileSubreddits' in timings:
		strList.append("\n\nProfiling subreddits, time: ")
		strList.append(str(counts['subredditsProfiled']))
		strList.append(", ")
		strList.append(str(round(timings['ProfileSubreddits'], 3)))

	if 'BackupDatabase' in timings:
		strList.append("\n\nBackup time: ")
		strList.append(str(round(timings['BackupDatabase'], 3)))

	if len(errors):
		strList.append("\n\nErrors: ")
		for error in errors:
			strList.append("\n")
			strList.append(error)


	return strList


couldNotUnderstandSection = (
	"Well, I got your message, but I didn't understand anything in it. "
	"If I should have, message /u/" + globals.OWNER_NAME + " and he'll look into it."
)

footer = (
	"|[^(FAQs)](https://np.reddit.com/r/UpdateMeBot/comments/4wirnm/updatemebot_info/)"
	"|[^(Request An Update)](http://np.reddit.com/message/compose/?to=" + globals.ACCOUNT_NAME + "&subject=Update&message="
	"Replace this text with a line starting with UpdateMe and then either a username and subreddit, "
	"or a link to a thread. You can also use SubscribeMe to get a message each time that user posts "
	"instead of just the next time"
	")"
	"|[^(Your Updates)](http://np.reddit.com/message/compose/?to=" + globals.ACCOUNT_NAME + "&subject=List Of Updates&message=MyUpdates)"
	"|[^(Remove All Updates)](http://np.reddit.com/message/compose/?to=" + globals.ACCOUNT_NAME + "&subject=Remove All Updates&message=RemoveAll)"
	"|[^(Feedback)](http://np.reddit.com/message/compose/?to=" + globals.OWNER_NAME + "&subject=UpdateMeBot Feedback)"
	"|[^(Code)](https://github.com/Watchful1/RedditSubsBot)"
	"\n|-|-|-|-|-|-|"
)