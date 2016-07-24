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

yourUpdatesMessage = (
	"Here are the people you asked me to update you on"
)

confirmationMessage = (
	"I'll update you next time /u/ posts in /r/"
)

couldNotSubscribeMessage = (
	"Sorry, I only work in these subreddits. Explanation"
)

alreadySubscribedMessage = ()

updatedSubscriptionMessage = ()

couldNotUnderstandMessage = (
	"Sorry, I couldn't understand your message."
)

deleteUpdatesConfirmationMessage = (
	"Okay, I won't remind you of any posts by /u/ in /r/. If you change your mind, do this"
)

deleteAllUpdatesConfirmationMessage = (
	"Okay, I won't remind you of any posts by anyone. If you change your mind, message me all or part of this list"
)

confirmationComment = (
	"I'll update you next time /u/ posts in /r/"
	"\n\nX people have clicked here to also be updated"
)