import discord_logging

log = discord_logging.get_logger(init=True)

import messages
import utils
import reddit_test


def test_add_reminder(database, reddit):
	created = utils.datetime_now()
	username = "Watchful1"
	subscribed_to = "AuthorName"
	database.get_or_add_user(subscribed_to)
	subreddit_name = "SubredditName"
	message = reddit_test.RedditObject(
		body=f"UpdateMe! u/{subscribed_to} r/{subreddit_name}",
		author=username,
		created=created
	)

	subreddit = database.get_or_add_subreddit(subreddit_name)
	subreddit.enabled = True
	database.commit()

	messages.process_message(message, reddit, database)
	result = message.get_first_child().body

	assert subscribed_to in result
	assert subreddit_name in result

	subscriptions = database.get_user_subscriptions_by_name(username)
	assert len(subscriptions) == 1
	assert subscriptions[0].subscriber.name == username
	assert subscriptions[0].subscribed_to.name == subscribed_to
	assert subscriptions[0].subreddit.name == subreddit_name
	assert subscriptions[0].recurring is False
