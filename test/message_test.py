import discord_logging

log = discord_logging.get_logger(init=True)

import messages
import utils
from praw_wrapper import reddit_test
import static
from classes.submission import Submission
from classes.subscription import Subscription
from classes.comment import DbComment
from classes.notification import Notification


def assert_message(message, included):
	for include in included:
		assert include in message


def assert_subscription(subscription, subscriber, author, subreddit, recurring, tag=None):
	assert subscription.subscriber.name == subscriber
	if author is None:
		assert subscription.author is None
	else:
		assert subscription.author.name == author
	assert subscription.subreddit.name == subreddit
	assert subscription.recurring is recurring
	assert subscription.tag == tag


def init_db(database, users=None, subreddits=None, default_subreddits=None, enable_tags=False):
	if users is not None:
		for user in users:
			database.get_or_add_user(user)

	if subreddits is not None:
		for subreddit_name in subreddits:
			subreddit = database.get_or_add_subreddit(subreddit_name)
			subreddit.is_enabled = True
			subreddit.tag_enabled = enable_tags

	if default_subreddits is not None:
		for subreddit_name in default_subreddits:
			subreddit = database.get_or_add_subreddit(subreddit_name)
			subreddit.is_enabled = True
			subreddit.tag_enabled = enable_tags
			subreddit.default_recurring = True
	database.commit()


def test_add_update(database, reddit):
	username = "Watchful1"
	author = "AuthorName"
	subreddit_name = "SubredditName"
	init_db(database, [author], [subreddit_name])
	message = reddit_test.RedditObject(
		body=f"UpdateMe! u/{author} r/{subreddit_name}",
		author=username
	)

	messages.process_message(message, reddit, database)
	assert_message(message.get_first_child().body, [author, subreddit_name, "next time"])

	subscriptions = database.get_user_subscriptions_by_name(username)
	assert len(subscriptions) == 1
	assert_subscription(subscriptions[0], username, author, subreddit_name, False)


def test_add_update_plus(database, reddit):
	username = "Watchful1"
	author = "AuthorName"
	subreddit_name = "SubredditName"
	init_db(database, [author], [subreddit_name])
	message = reddit_test.RedditObject(
		body=f"UpdateMe!+u/{author}+r/{subreddit_name}",
		author=username
	)

	messages.process_message(message, reddit, database)
	assert_message(message.get_first_child().body, [author, subreddit_name, "next time"])

	subscriptions = database.get_user_subscriptions_by_name(username)
	assert len(subscriptions) == 1
	assert_subscription(subscriptions[0], username, author, subreddit_name, False)


def test_add_subscribe(database, reddit):
	username = "Watchful1"
	author = "AuthorName"
	subreddit_name = "SubredditName"
	init_db(database, [author], [subreddit_name])
	message = reddit_test.RedditObject(
		body=f"SubscribeMe! u/{author} r/{subreddit_name}",
		author=username
	)

	messages.process_message(message, reddit, database)
	assert_message(message.get_first_child().body, [author, subreddit_name, "each time"])

	subscriptions = database.get_user_subscriptions_by_name(username)
	assert len(subscriptions) == 1
	assert_subscription(subscriptions[0], username, author, subreddit_name, True)


def test_add_subscribe_subreddit(database, reddit):
	username = "Watchful1"
	subreddit_name = "SubredditName"
	init_db(database, [], [subreddit_name])
	message = reddit_test.RedditObject(
		body=f"SubscribeMe! r/{subreddit_name} -all",
		author=username
	)

	messages.process_message(message, reddit, database)
	assert_message(message.get_first_child().body, [subreddit_name, "each post"])

	subscriptions = database.get_user_subscriptions_by_name(username)
	assert len(subscriptions) == 1
	assert_subscription(subscriptions[0], username, None, subreddit_name, True)


def test_update_subscribe(database, reddit):
	username = "Watchful1"
	author = "AuthorName"
	subreddit_name = "SubredditName"
	database.add_subscription(
		Subscription(
			database.get_or_add_user(username),
			database.get_or_add_user(author),
			database.get_or_add_subreddit(subreddit_name),
			False
		)
	)
	database.commit()
	message = reddit_test.RedditObject(
		body=f"SubscribeMe! u/{author} r/{subreddit_name}",
		author=username
	)

	messages.process_message(message, reddit, database)
	assert_message(
		message.get_first_child().body,
		[author, subreddit_name, "updated your subscription", "each"])

	subscriptions = database.get_user_subscriptions_by_name(username, only_enabled=False)
	assert len(subscriptions) == 1
	assert_subscription(subscriptions[0], username, author, subreddit_name, True)


def test_already_subscribed(database, reddit):
	username = "Watchful1"
	author = "AuthorName"
	subreddit_name = "SubredditName"
	database.add_subscription(
		Subscription(
			database.get_or_add_user(username),
			database.get_or_add_user(author),
			database.get_or_add_subreddit(subreddit_name),
			True
		)
	)
	database.commit()
	message = reddit_test.RedditObject(
		body=f"SubscribeMe! u/{author} r/{subreddit_name}",
		author=username
	)

	messages.process_message(message, reddit, database)
	assert_message(
		message.get_first_child().body,
		[author, subreddit_name, "already asked me", "each"])

	subscriptions = database.get_user_subscriptions_by_name(username, only_enabled=False)
	assert len(subscriptions) == 1
	assert_subscription(subscriptions[0], username, author, subreddit_name, True)


def test_subreddit_not_enabled(database, reddit):
	username = "Watchful1"
	author = "AuthorName"
	subreddit_name = "SubredditName"
	message = reddit_test.RedditObject(
		body=f"UpdateMe! u/{author} r/{subreddit_name}",
		author=username
	)

	messages.process_message(message, reddit, database)
	assert_message(message.get_first_child().body, ["is not being tracked"])

	subscriptions = database.get_user_subscriptions_by_name(username, only_enabled=False)
	assert len(subscriptions) == 1
	assert_subscription(subscriptions[0], username, author.lower(), subreddit_name.lower(), False)


def test_add_link(database, reddit):
	username = "Watchful1"
	author = "AuthorName"
	subreddit_name = "SubredditName"
	init_db(database, [author], [subreddit_name])
	post_id = reddit_test.random_id()
	reddit.add_submission(
		reddit_test.RedditObject(
			id=post_id,
			author=author,
			subreddit=subreddit_name
		)
	)
	message = reddit_test.RedditObject(
		body=f"https://www.reddit.com/r/updateme/comments/{post_id}/this_is_a_test_post/",
		author=username
	)

	messages.process_message(message, reddit, database)
	assert_message(message.get_first_child().body, [author, subreddit_name, "next time"])

	subscriptions = database.get_user_subscriptions_by_name(username)
	assert len(subscriptions) == 1
	assert_subscription(subscriptions[0], username, author, subreddit_name, False)


def test_add_link_with_tag(database, reddit):
	username = "Watchful1"
	author = database.get_or_add_user("AuthorName")
	subreddit_name = "SubredditName"
	tag = "this is a tag"
	init_db(database, [author.name], [subreddit_name], enable_tags=True)
	submission_id = reddit_test.random_id()
	db_submission = Submission(
		submission_id=submission_id,
		time_created=utils.datetime_now(),
		author=author,
		subreddit=database.get_or_add_subreddit(subreddit_name),
		permalink=f"/r/{subreddit_name}/comments/{submission_id}/",
		tag=tag
	)
	database.add_submission(db_submission)
	message = reddit_test.RedditObject(
		body=f"https://www.reddit.com/r/{subreddit_name}/comments/{submission_id}/this_is_a_test_post/",
		author=username
	)

	messages.process_message(message, reddit, database)
	assert_message(message.get_first_child().body, [author.name, subreddit_name, "next time"])

	subscriptions = database.get_user_subscriptions_by_name(username)
	assert len(subscriptions) == 1
	assert_subscription(subscriptions[0], username, author.name, subreddit_name, False, tag)


def test_add_link_default_subscribe(database, reddit):
	username = "Watchful1"
	author = "AuthorName"
	subreddit_name = "SubredditName"
	init_db(database, [author], None, [subreddit_name])
	post_id = reddit_test.random_id()
	reddit.add_submission(
		reddit_test.RedditObject(
			id=post_id,
			author=author,
			subreddit=subreddit_name
		)
	)
	message = reddit_test.RedditObject(
		body=f"https://www.reddit.com/r/updateme/comments/{post_id}/this_is_a_test_post/",
		author=username
	)

	messages.process_message(message, reddit, database)
	assert_message(message.get_first_child().body, [author, subreddit_name, "each time"])

	subscriptions = database.get_user_subscriptions_by_name(username)
	assert len(subscriptions) == 1
	assert_subscription(subscriptions[0], username, author, subreddit_name, True)


def test_remove_subscription(database, reddit):
	username = "Watchful1"
	author = "AuthorName"
	subreddit_name = "SubredditName"
	database.add_subscription(
		Subscription(
			database.get_or_add_user(username),
			database.get_or_add_user(author),
			database.get_or_add_subreddit(subreddit_name),
			True
		)
	)
	database.commit()
	message = reddit_test.RedditObject(
		body=f"Remove! u/{author} r/{subreddit_name}",
		author=username
	)

	messages.process_message(message, reddit, database)
	assert_message(
		message.get_first_child().body,
		[author, subreddit_name, "removed your subscription"])

	subscriptions = database.get_user_subscriptions_by_name(username)
	assert len(subscriptions) == 0


def test_remove_subscription_with_notifications(database, reddit):
	subscriber = database.get_or_add_user("User1")
	subscriber2 = database.get_or_add_user("User2")
	author = database.get_or_add_user("AuthorName")
	subreddit = database.get_or_add_subreddit("SubredditName")
	subscription = Subscription(subscriber, author, subreddit, True)
	database.add_subscription(subscription)
	subscription2 = Subscription(subscriber2, author, subreddit, True)
	database.add_subscription(subscription2)
	submission = Submission(reddit_test.random_id(), utils.datetime_now(), author, subreddit,	"")
	database.add_submission(submission)
	notification = Notification(subscription, submission)
	database.add_notification(notification)
	notification = Notification(subscription2, submission)
	database.add_notification(notification)
	database.commit()

	message = reddit_test.RedditObject(
		body=f"Remove! u/{author.name} r/{subreddit.name}",
		author=subscriber.name
	)

	messages.process_message(message, reddit, database)

	assert len(database.get_pending_notifications()) == 1


def test_remove_tagged_subscription(database, reddit):
	username = "Watchful1"
	author = "AuthorName"
	subreddit_name = "SubredditName"
	tag = "this is a tag"
	database.add_subscription(
		Subscription(
			database.get_or_add_user(username),
			database.get_or_add_user(author),
			database.get_or_add_subreddit(subreddit_name),
			True,
			tag
		)
	)
	database.commit()
	message = reddit_test.RedditObject(
		body=f"Remove! u/{author} r/{subreddit_name} <{tag}>",
		author=username
	)

	messages.process_message(message, reddit, database)
	assert_message(
		message.get_first_child().body,
		[author, subreddit_name, "removed your subscription", "with tag", tag])

	subscriptions = database.get_user_subscriptions_by_name(username)
	assert len(subscriptions) == 0


def test_remove_all_tagged_subscriptions(database, reddit):
	username = "Watchful1"
	author = "AuthorName"
	subreddit_name = "SubredditName"
	database.add_subscription(
		Subscription(
			database.get_or_add_user(username),
			database.get_or_add_user(author),
			database.get_or_add_subreddit(subreddit_name),
			False,
			"this is a tag"
		)
	)
	database.add_subscription(
		Subscription(
			database.get_or_add_user(username),
			database.get_or_add_user(author),
			database.get_or_add_subreddit(subreddit_name),
			False,
			"this is another tag"
		)
	)
	database.commit()
	message = reddit_test.RedditObject(
		body=f"Remove! u/{author} r/{subreddit_name}",
		author=username
	)

	messages.process_message(message, reddit, database)
	assert_message(
		message.get_first_child().body,
		[author, subreddit_name, "removed all your tagged subscriptions"])

	subscriptions = database.get_user_subscriptions_by_name(username)
	assert len(subscriptions) == 0


def test_remove_global_subscription(database, reddit):
	username = "Watchful1"
	subreddit_name = "SubredditName"
	database.add_subscription(
		Subscription(
			database.get_or_add_user(username),
			None,
			database.get_or_add_subreddit(subreddit_name),
			True
		)
	)
	database.commit()
	message = reddit_test.RedditObject(
		body=f"Remove! r/{subreddit_name} -all",
		author=username
	)

	messages.process_message(message, reddit, database)
	assert_message(
		message.get_first_child().body,
		[subreddit_name, "removed your subscription in"])

	subscriptions = database.get_user_subscriptions_by_name(username)
	assert len(subscriptions) == 0


def test_remove_all_subscription(database, reddit):
	username = "Watchful1"
	database.add_subscription(
		Subscription(
			database.get_or_add_user(username),
			database.get_or_add_user("Author1"),
			database.get_or_add_subreddit("Subreddit1", enable_subreddit_if_new=True),
			True
		)
	)
	database.add_subscription(
		Subscription(
			database.get_or_add_user(username),
			database.get_or_add_user("Author2"),
			database.get_or_add_subreddit("Subreddit2", enable_subreddit_if_new=True),
			True
		)
	)
	database.commit()
	message = reddit_test.RedditObject(
		body=f"RemoveAll",
		author=username
	)

	messages.process_message(message, reddit, database)
	assert_message(
		message.get_first_child().body,
		["Author1", "Author2", "Subreddit1", "Subreddit2", "Removed your subscription"])

	subscriptions = database.get_user_subscriptions_by_name(username, only_enabled=False)
	assert len(subscriptions) == 0


def test_remove_all_subscription_with_notifications(database, reddit):
	subscriber = database.get_or_add_user("User1")
	subscriber2 = database.get_or_add_user("User2")
	author1 = database.get_or_add_user("Author1")
	author2 = database.get_or_add_user("Author2")
	subreddit = database.get_or_add_subreddit("SubredditName", enable_subreddit_if_new=True)

	subscription = Subscription(subscriber, author1, subreddit, True)
	database.add_subscription(subscription)
	subscription2 = Subscription(subscriber2, author1, subreddit, True)
	database.add_subscription(subscription2)
	subscription3 = Subscription(subscriber, author2, subreddit, True)
	database.add_subscription(subscription3)
	subscription4 = Subscription(subscriber2, author2, subreddit, True)
	database.add_subscription(subscription4)

	submission1 = Submission(reddit_test.random_id(), utils.datetime_now(), author1, subreddit, "")
	database.add_submission(submission1)
	submission2 = Submission(reddit_test.random_id(), utils.datetime_now(), author2, subreddit, "")
	database.add_submission(submission2)

	notification = Notification(subscription, submission1)
	database.add_notification(notification)
	notification = Notification(subscription2, submission1)
	database.add_notification(notification)
	notification = Notification(subscription3, submission2)
	database.add_notification(notification)
	notification = Notification(subscription4, submission2)
	database.add_notification(notification)

	database.commit()

	message = reddit_test.RedditObject(body="RemoveAll", author=subscriber.name)

	messages.process_message(message, reddit, database)

	assert len(database.get_pending_notifications()) == 2


def test_delete_comment(database, reddit):
	username = "Watchful1"
	author = database.get_or_add_user("AuthorName")
	subreddit_name = "SubredditName"
	reddit_comment = reddit_test.RedditObject(
		author=username,
		link_id=reddit_test.random_id()
	)
	reddit.add_comment(reddit_comment)
	db_submission = Submission(
		submission_id=reddit_comment.link_id,
		time_created=utils.datetime_now(),
		author=author,
		subreddit=database.get_or_add_subreddit(subreddit_name, enable_subreddit_if_new=True),
		permalink=f"none"
	)
	database.add_submission(db_submission)
	database.add_comment(
		DbComment(
			comment_id=reddit_comment.id,
			submission=db_submission,
			subscriber=database.get_or_add_user(username),
			author=author,
			subreddit=database.get_or_add_subreddit(subreddit_name),
			recurring=True
		)
	)
	database.commit()
	message = reddit_test.RedditObject(
		body=f"delete {reddit_comment.link_id}",
		author=username
	)

	messages.process_message(message, reddit, database)
	assert_message(message.get_first_child().body, ["Comment deleted"])


def test_delete_comment_not_author(database, reddit):
	username = "Watchful1"
	author = database.get_or_add_user("AuthorName")
	subreddit_name = "SubredditName"
	reddit_comment = reddit_test.RedditObject(
		author=username,
		link_id=reddit_test.random_id()
	)
	reddit.add_comment(reddit_comment)
	db_submission = Submission(
		submission_id=reddit_comment.link_id,
		time_created=utils.datetime_now(),
		author=author,
		subreddit=database.get_or_add_subreddit(subreddit_name, enable_subreddit_if_new=True),
		permalink=f"none"
	)
	database.add_submission(db_submission)
	database.add_comment(
		DbComment(
			comment_id=reddit_comment.id,
			submission=db_submission,
			subscriber=database.get_or_add_user(username),
			author=author,
			subreddit=database.get_or_add_subreddit(subreddit_name),
			recurring=True
		)
	)
	database.commit()
	message = reddit_test.RedditObject(
		body=f"delete {reddit_comment.link_id}",
		author="Watchful2"
	)

	messages.process_message(message, reddit, database)
	assert_message(message.get_first_child().body, ["looks like the bot wasn't replying"])


def test_delete_comment_doesnt_exist(database, reddit):
	message = reddit_test.RedditObject(
		body=f"delete {reddit_test.random_id()}",
		author="Watchful1"
	)

	messages.process_message(message, reddit, database)
	assert_message(message.get_first_child().body, ["comment doesn't exist or was already"])


def test_list(database, reddit):
	username = "Watchful1"
	database.add_subscription(
		Subscription(
			database.get_or_add_user(username),
			database.get_or_add_user("Author1"),
			database.get_or_add_subreddit("Subreddit1", enable_subreddit_if_new=True),
			True
		)
	)
	database.add_subscription(
		Subscription(
			database.get_or_add_user(username),
			database.get_or_add_user("Author2"),
			database.get_or_add_subreddit("Subreddit2", enable_subreddit_if_new=True),
			False
		)
	)
	database.add_subscription(
		Subscription(
			database.get_or_add_user("Watchful2"),
			database.get_or_add_user("Author3"),
			database.get_or_add_subreddit("Subreddit3", enable_subreddit_if_new=True),
			False
		)
	)
	database.commit()
	message = reddit_test.RedditObject(
		body=f"MySubscriptions",
		author=username
	)

	messages.process_message(message, reddit, database)
	response = message.get_first_child().body
	assert "Author1" in response
	assert "Author2" in response
	assert "Subreddit1" in response
	assert "Subreddit2" in response
	assert "Each" in response
	assert "Next" in response
	assert "Author3" not in response
	assert "Subreddit3" not in response


def test_list_tagged(database, reddit):
	username = "Watchful1"
	database.add_subscription(
		Subscription(
			database.get_or_add_user(username),
			database.get_or_add_user("Author1"),
			database.get_or_add_subreddit("Subreddit1", enable_subreddit_if_new=True),
			True,
			"this is a tag"
		)
	)
	database.add_subscription(
		Subscription(
			database.get_or_add_user(username),
			database.get_or_add_user("Author2"),
			database.get_or_add_subreddit("Subreddit2", enable_subreddit_if_new=True),
			False,
			"this is also a tag"
		)
	)
	database.add_subscription(
		Subscription(
			database.get_or_add_user("Watchful2"),
			database.get_or_add_user("Author3"),
			database.get_or_add_subreddit("Subreddit3", enable_subreddit_if_new=True),
			False
		)
	)
	database.commit()
	message = reddit_test.RedditObject(
		body=f"MySubscriptions",
		author=username
	)

	messages.process_message(message, reddit, database)
	response = message.get_first_child().body
	assert "Author1" in response
	assert "Author2" in response
	assert "Subreddit1" in response
	assert "Subreddit2" in response
	assert "Each" in response
	assert "Next" in response
	assert "Author3" not in response
	assert "Subreddit3" not in response
	assert "<this is a tag>" in response
	assert "<this is also a tag>" in response


def test_add_sub(database, reddit):
	database.get_or_add_subreddit("Subreddit1")
	database.commit()
	message = reddit_test.RedditObject(
		body="AddSubreddit r/Subreddit1 subscribe",
		author=static.OWNER
	)
	messages.process_message(message, reddit, database)

	response = message.get_first_child().body
	assert "Activated r/Subreddit1" in response
	assert "as subscribe" in response

	subreddit = database.get_or_add_subreddit("Subreddit1")
	assert subreddit.is_enabled is True
	assert subreddit.default_recurring is True


def test_add_update_tagged(database, reddit):
	username = "Watchful1"
	author = "AuthorName"
	subreddit_name = "SubredditName"
	tag = "this is a tag"
	init_db(database, [author], [subreddit_name], enable_tags=True)
	message = reddit_test.RedditObject(
		body=f"UpdateMe! u/{author} r/{subreddit_name} <{tag}>",
		author=username
	)

	messages.process_message(message, reddit, database)
	assert_message(message.get_first_child().body, [author, subreddit_name, "next time", tag])

	subscriptions = database.get_user_subscriptions_by_name(username)
	assert len(subscriptions) == 1
	assert_subscription(subscriptions[0], username, author, subreddit_name, False, tag)


def test_subscribe_existing_tagged(database, reddit):
	username = "Watchful1"
	author = "AuthorName"
	subreddit_name = "SubredditName"
	init_db(database, [author], [subreddit_name], enable_tags=True)
	database.add_subscription(
		Subscription(
			database.get_or_add_user(username),
			database.get_or_add_user(author),
			database.get_or_add_subreddit(subreddit_name),
			True,
			"another tag"
		)
	)
	database.add_subscription(
		Subscription(
			database.get_or_add_user(username),
			database.get_or_add_user(author),
			database.get_or_add_subreddit(subreddit_name),
			True,
			"this is a tag"
		)
	)
	database.commit()
	message = reddit_test.RedditObject(
		body=f"SubscribeMe! u/{author} r/{subreddit_name}",
		author=username
	)

	messages.process_message(message, reddit, database)
	assert_message(message.get_first_child().body, [author, subreddit_name, "each time", "This replaces"])

	subscriptions = database.get_user_subscriptions_by_name(username)
	assert len(subscriptions) == 1
	assert_subscription(subscriptions[0], username, author, subreddit_name, True, None)


def test_subscribe_tagged_existing_all(database, reddit):
	username = "Watchful1"
	author = "AuthorName"
	subreddit_name = "SubredditName"
	init_db(database, [author], [subreddit_name], enable_tags=True)
	database.add_subscription(
		Subscription(
			database.get_or_add_user(username),
			database.get_or_add_user(author),
			database.get_or_add_subreddit(subreddit_name),
			True
		)
	)
	database.commit()
	message = reddit_test.RedditObject(
		body=f"SubscribeMe! u/{author} r/{subreddit_name} <this is a tag>",
		author=username
	)

	messages.process_message(message, reddit, database)
	assert_message(message.get_first_child().body, [author, subreddit_name, "You're already"])

	subscriptions = database.get_user_subscriptions_by_name(username)
	assert len(subscriptions) == 1


def test_add_link_tagged(database, reddit):
	username = "Watchful1"
	author = "AuthorName"
	subreddit_name = "SubredditName"
	init_db(database, [author], [subreddit_name])
	post_id = reddit_test.random_id()
	reddit.add_submission(
		reddit_test.RedditObject(
			id=post_id,
			author=author,
			subreddit=subreddit_name
		)
	)
	message = reddit_test.RedditObject(
		body=f"https://www.reddit.com/r/updateme/comments/{post_id}/this_is_a_test_post/",
		author=username
	)

	messages.process_message(message, reddit, database)
	assert_message(message.get_first_child().body, [author, subreddit_name, "next time"])

	subscriptions = database.get_user_subscriptions_by_name(username)
	assert len(subscriptions) == 1
	assert_subscription(subscriptions[0], username, author, subreddit_name, False)


def test_short_notifs(database, reddit):
	message = reddit_test.RedditObject(
		body="Short",
		author="User1"
	)
	messages.process_message(message, reddit, database)

	response = message.get_first_child().body
	assert "You'll now get shortened notifications" in response

	user = database.get_or_add_user("User1")
	assert user.short_notifs is True


def test_long_notifs(database, reddit):
	message = reddit_test.RedditObject(
		body="Long",
		author="User1"
	)
	messages.process_message(message, reddit, database)

	response = message.get_first_child().body
	assert "You'll now get normal notifications" in response

	user = database.get_or_add_user("User1")
	assert user.short_notifs is False
