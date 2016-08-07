import globals


def messageSubject(user):
	return (
		"Hello {user}, UpdateMeBot Here!"
	).format(
		user=user
	)


def alertMessage(subscribedTo, subreddit, link):
	return (
		"UpdateMeBot here!"
		"\n\n/u/{subscribedTo} has posted a new thread in /r/{subreddit}"
		"\n\nYou can find it here:"
		"\n\n{link}"
	).format(
		subscribedTo=subscribedTo,
		subreddit=subreddit,
		link=link
	)

	# are you still subscribed? do you want to be?


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


couldNotSubscribeSection = (
	"Sorry, I only work in these subreddits. Explanation"
)


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


def removeUpdatesConfirmationMessage(removedList):
	strList = ["I will no longer message when the following happens. "
			   "If you change your mind, you can copy the below section into a message to me"]

	for removed in removedList:
		strList.append("  \n")
		strList.extend(eachHelper(removed))

	return strList


couldNotUnderstandMessage = (
	"Well, I got your message, but I didn't understand anything in it. "
	"If I should have, message /u/"+globals.OWNER_NAME+" and he'll look into it."
)

footer = (
	"|[^(FAQs)](https://www.reddit.com/r/UpdateMeBot/comments/4wirnm/updatemebot_info/)"
	"|[^(Request An Update)](http://np.reddit.com/message/compose/?to="+globals.ACCOUNT_NAME+"&subject=Update&message="
		"Replace this text with either a link to a thread, or a line starting with UpdateMe and then a username and subreddit."
		"You can also use SubscribeMe to get a message each time that user posts instead of just the next time"
	    ")"
	"|[^(Your Updates)](http://np.reddit.com/message/compose/?to="+globals.ACCOUNT_NAME+"&subject=List Of Updates&message=MyUpdates)"
	"|[^(Remove All Updates)](http://np.reddit.com/message/compose/?to="+globals.ACCOUNT_NAME+"&subject=Remove All Updates&message=RemoveAll)"
	"|[^(Feedback)](http://np.reddit.com/message/compose/?to="+globals.OWNER_NAME+"&subject=UpdateMeBot Feedback)"
	"|[^(Code)](https://github.com/Watchful1/RedditSubsBot)"
	"\n|-|-|-|-|-|-|"
)

confirmationComment = (
	"I'll update you next time /u/ posts in /r/"
	"\n\nX people have clicked here to also be updated"
)
