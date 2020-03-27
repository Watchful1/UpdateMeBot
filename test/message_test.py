import discord_logging

log = discord_logging.get_logger(init=True)

import messages
import utils
import reddit_test
from classes.subscription import Subscription


def assert_message(message, included):
	for include in included:
		assert include in message


def assert_subscription(subscription, subscriber, subscribed_to, subreddit, recurring):
	assert subscription.subscriber.name == subscriber
	assert subscription.subscribed_to.name == subscribed_to
	assert subscription.subreddit.name == subreddit
	assert subscription.recurring is recurring


def init_db(database, users=None, subreddits=None, default_subreddits=None):
	if users is not None:
		for user in users:
			database.get_or_add_user(user)

	if subreddits is not None:
		for subreddit_name in subreddits:
			subreddit = database.get_or_add_subreddit(subreddit_name)
			subreddit.enabled = True

	if default_subreddits is not None:
		for subreddit_name in default_subreddits:
			subreddit = database.get_or_add_subreddit(subreddit_name)
			subreddit.enabled = True
			subreddit.default_recurring = True
	database.commit()


def test_add_update(database, reddit):
	username = "Watchful1"
	subscribed_to = "AuthorName"
	subreddit_name = "SubredditName"
	init_db(database, [subscribed_to], [subreddit_name])
	message = reddit_test.RedditObject(
		body=f"UpdateMe! u/{subscribed_to} r/{subreddit_name}",
		author=username
	)

	messages.process_message(message, reddit, database)
	assert_message(message.get_first_child().body, [subscribed_to, subreddit_name, "next time"])

	subscriptions = database.get_user_subscriptions_by_name(username)
	assert len(subscriptions) == 1
	assert_subscription(subscriptions[0], username, subscribed_to, subreddit_name, False)


def test_add_subscribe(database, reddit):
	username = "Watchful1"
	subscribed_to = "AuthorName"
	subreddit_name = "SubredditName"
	init_db(database, [subscribed_to], [subreddit_name])
	message = reddit_test.RedditObject(
		body=f"SubscribeMe! u/{subscribed_to} r/{subreddit_name}",
		author=username
	)

	messages.process_message(message, reddit, database)
	assert_message(message.get_first_child().body, [subscribed_to, subreddit_name, "each time"])

	subscriptions = database.get_user_subscriptions_by_name(username)
	assert len(subscriptions) == 1
	assert_subscription(subscriptions[0], username, subscribed_to, subreddit_name, True)


def test_update_subscribe(database, reddit):
	username = "Watchful1"
	subscribed_to = "AuthorName"
	subreddit_name = "SubredditName"
	database.add_subscription(
		Subscription(
			database.get_or_add_user(username),
			database.get_or_add_user(subscribed_to),
			database.get_or_add_subreddit(subreddit_name),
			False
		)
	)
	database.commit()
	message = reddit_test.RedditObject(
		body=f"SubscribeMe! u/{subscribed_to} r/{subreddit_name}",
		author=username
	)

	messages.process_message(message, reddit, database)
	assert_message(
		message.get_first_child().body,
		[subscribed_to, subreddit_name, "updated your subscription", "each"])

	subscriptions = database.get_user_subscriptions_by_name(username)
	assert len(subscriptions) == 1
	assert_subscription(subscriptions[0], username, subscribed_to, subreddit_name, True)


def test_already_subscribed(database, reddit):
	username = "Watchful1"
	subscribed_to = "AuthorName"
	subreddit_name = "SubredditName"
	database.add_subscription(
		Subscription(
			database.get_or_add_user(username),
			database.get_or_add_user(subscribed_to),
			database.get_or_add_subreddit(subreddit_name),
			True
		)
	)
	database.commit()
	message = reddit_test.RedditObject(
		body=f"SubscribeMe! u/{subscribed_to} r/{subreddit_name}",
		author=username
	)

	messages.process_message(message, reddit, database)
	assert_message(
		message.get_first_child().body,
		[subscribed_to, subreddit_name, "already asked me", "each"])

	subscriptions = database.get_user_subscriptions_by_name(username)
	assert len(subscriptions) == 1
	assert_subscription(subscriptions[0], username, subscribed_to, subreddit_name, True)


def test_subreddit_not_enabled(database, reddit):
	username = "Watchful1"
	subscribed_to = "AuthorName"
	subreddit_name = "SubredditName"
	message = reddit_test.RedditObject(
		body=f"UpdateMe! u/{subscribed_to} r/{subreddit_name}",
		author=username
	)

	messages.process_message(message, reddit, database)
	assert_message(message.get_first_child().body, ["is not being tracked"])

	subscriptions = database.get_user_subscriptions_by_name(username)
	assert len(subscriptions) == 1
	assert_subscription(subscriptions[0], username, subscribed_to.lower(), subreddit_name.lower(), False)


def test_add_link(database, reddit):
	username = "Watchful1"
	subscribed_to = "AuthorName"
	subreddit_name = "SubredditName"
	init_db(database, [subscribed_to], [subreddit_name])
	post_id = utils.random_id()
	reddit.add_submission(
		reddit_test.RedditObject(
			id=post_id,
			author=subscribed_to,
			subreddit=reddit_test.Subreddit(subreddit_name)
		)
	)
	message = reddit_test.RedditObject(
		body=f"https://www.reddit.com/r/updateme/comments/{post_id}/this_is_a_test_post/",
		author=username
	)

	messages.process_message(message, reddit, database)
	assert_message(message.get_first_child().body, [subscribed_to, subreddit_name, "next time"])

	subscriptions = database.get_user_subscriptions_by_name(username)
	assert len(subscriptions) == 1
	assert_subscription(subscriptions[0], username, subscribed_to, subreddit_name, False)


def test_add_link_default_subscribe(database, reddit):
	username = "Watchful1"
	subscribed_to = "AuthorName"
	subreddit_name = "SubredditName"
	init_db(database, [subscribed_to], None, [subreddit_name])
	post_id = utils.random_id()
	reddit.add_submission(
		reddit_test.RedditObject(
			id=post_id,
			author=subscribed_to,
			subreddit=reddit_test.Subreddit(subreddit_name)
		)
	)
	message = reddit_test.RedditObject(
		body=f"https://www.reddit.com/r/updateme/comments/{post_id}/this_is_a_test_post/",
		author=username
	)

	messages.process_message(message, reddit, database)
	assert_message(message.get_first_child().body, [subscribed_to, subreddit_name, "each time"])

	subscriptions = database.get_user_subscriptions_by_name(username)
	assert len(subscriptions) == 1
	assert_subscription(subscriptions[0], username, subscribed_to, subreddit_name, True)
