This is a python reddit bot that allows users to subscribe to posts by authors in certain subreddits.

Credit to Silver-- of RemindMeBot, TheDarkLordSano of HFYSubsBot and SmBe19 of various bots for inspiration, ideas and code snippits. Also Stuck_In_the_Matrix for pushshift.io, which is used to search comments.

(updateme|subscribeme ((/r/subreddit)+ (/u/user)+)|((reddit.com...)+))|(http...)
	Add a subscription to a user in a subreddit. Updateme subscriptions only last one post, subscribeme ones last until canceled.

	Supports adding a subscription to a single user in multiple subreddits, or multiple users in a single subreddit. Also supports passing a link to the post. If a link is passed by itself, it uses the subreddits default subscription mode.

removeall
	Remove all subscriptions. The response lists all the subscriptions that were removed in a format that if copied and messaged back to the bot readds them all.

remove (/r/subreddit)+ (/u/user)+
	Removes the subscription to a user in a subreddit. Supports removing one user from multiple subreddits or multiple users from one subreddit.

(mysubscriptions|myupdates)
	Lists all of the users subscriptions

deletecomment (t3_threadid)
	Deletes a response comment if it's unwanted. Only works if the message comes from the author of the response comments parent. A link to this is embedded in the response comment.

(addsubreddit|addsubredditsub) (/r/subreddit)+
	Adds a subreddit to the bot and notifies all the users who have previously requested it. Supports multiple subreddits. If subredditsub is used, the default for the subreddit is set to subscription, otherwise it's set to update. Can also be used to update a subreddit's default.

	ADMIN ONLY

(subredditpmtrue|subredditpmfalse) (/r/subreddit)+
	Sets or unsets a subreddit to only pm users and never post responses publicly. Supports multiple subreddits.

	ADMIN ONLY

(leavemealone|talktome) </r/subreddit>+ </u/user>+
	Blacklists or removes from the blacklist a user or subreddit. If blacklisted, the bot will not interact with that user or subreddit.

	If passed with no arguments, uses the author of the message.

	If sent by an admin, takes any number of subreddits and/or users to blacklist.

(prompt|dontprompt) (/r/subreddit)+ </u/users>+
	Adds or removes a prompt on each post asking if anyone wants to subscribe. Only accepts max one user and subreddit.

	If sent with with no users, adds the prompt for the message author in the specified subreddit.

	If sent by an admin, takes a subreddit and user to add the prompt for. If /u/sub is used, prompts for all users in subreddit.




Commands must be contained within one line with no newline characters. A single newline does not render with reddits markdown, but the bot considers it a new line.

You can specify multiple commands in a message as long as they are seperated by newlines.