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


def eachHelper(item, includeMessageType = True):
	strList = []
	if item['single']:
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
	for subreddit in subreddits:
		strList.append("/r/")
		strList.append(subreddit)
		if length != 1 and i+2 == length:
			strList.append(" or ")
		elif length != 1 and i+1 != length:
			strList.append(", ")
		i += 1

	strList.append(".\n\n")
	strList.append("This bot works by checking every subreddit that someone is subscribed to every few minutes. ")
	strList.append("Each subreddit it checks takes several seconds, so I have to limit the number of subreddits or the bot will get overloaded. ")
	strList.append("If you think this would be a good subreddit for this bot, message /u/"+globals.OWNER_NAME+" and he'll take a look. ")
	strList.append("I've also logged your request, so if the subreddit does get added, I'll automatically start sending your updates.")

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
			   "If you change your mind, you can copy the below section into a message to me"]

	for removed in removedList:
		strList.append("  \n")
		strList.extend(eachHelper(removed))

	return strList


def activatingSubredditMessage(subreddit, subscriptions):
	strList = ["/r/",subreddit," has been added to this bot. Following is the list of users you requested to be subscribed to.\n\n"]

	for subscription in subscriptions:
		if subscription['single']:
			strList.append("UpdateMe")
		else:
			strList.append("SubscribeMe")
		strList.append(" /u/")
		strList.append(subscription['subscribedTo'])
		strList.append("  \n")

	strList.append("\n\nNote, your subscription automatically starts at the time of your original request, so if it's been a while you might get a flood of messages.")

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


def subredditNoticeThresholdMessage(subreddit, count):
	return ["/r/", subreddit, " has hit the notice threshold, which is ", str(count)]


def longRunMessage(seconds):
	return ["Loop run took too long: ", str(seconds)]


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
	strList.append("Oldest found timestamp: ")
	strList.append("\n\n")
	strList.append("Recorded timestamp: ")


def possibleMissedPostMessage(oldestTimestamp, recordedTimestamp, subreddit):
	strList = ["Post search hit index 99 without finding oldest timestamp in /r/",subreddit,"\n\n"]
	strList.append("Oldest found timestamp: ")
	strList.append("\n\n")
	strList.append("Recorded timestamp: ")


couldNotUnderstandSection = (
	"Well, I got your message, but I didn't understand anything in it. "
	"If I should have, message /u/"+globals.OWNER_NAME+" and he'll look into it."
)

footer = (
	"|[^(FAQs)](https://np.reddit.com/r/UpdateMeBot/comments/4wirnm/updatemebot_info/)"
	"|[^(Request An Update)](http://np.reddit.com/message/compose/?to="+globals.ACCOUNT_NAME+"&subject=Update&message="
		"Replace this text with a line starting with UpdateMe and then either a username and subreddit, or a link to a thread."
		"You can also use SubscribeMe to get a message each time that user posts instead of just the next time"
	    ")"
	"|[^(Your Updates)](http://np.reddit.com/message/compose/?to="+globals.ACCOUNT_NAME+"&subject=List Of Updates&message=MyUpdates)"
	"|[^(Remove All Updates)](http://np.reddit.com/message/compose/?to="+globals.ACCOUNT_NAME+"&subject=Remove All Updates&message=RemoveAll)"
	"|[^(Feedback)](http://np.reddit.com/message/compose/?to="+globals.OWNER_NAME+"&subject=UpdateMeBot Feedback)"
	"|[^(Code)](https://github.com/Watchful1/RedditSubsBot)"
	"\n|-|-|-|-|-|-|"
)