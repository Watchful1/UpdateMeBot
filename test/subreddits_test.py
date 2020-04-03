import discord_logging
from datetime import datetime
from datetime import timedelta

log = discord_logging.get_logger(init=True)

import subreddits
import reddit_test
import utils


def add_new_post_to_sub(subreddit, delta):
	subreddit.posts.append(reddit_test.RedditObject(created=utils.datetime_now() - delta))


def test_profile_subreddits(database, reddit):
	reddit_subreddit = reddit_test.Subreddit("Subreddit1")
	add_new_post_to_sub(reddit_subreddit, timedelta(minutes=5))
	add_new_post_to_sub(reddit_subreddit, timedelta(minutes=6))
	add_new_post_to_sub(reddit_subreddit, timedelta(hours=1, minutes=7))
	add_new_post_to_sub(reddit_subreddit, timedelta(hours=1, minutes=8))
	add_new_post_to_sub(reddit_subreddit, timedelta(hours=2, minutes=1))
	add_new_post_to_sub(reddit_subreddit, timedelta(hours=3, minutes=2))
	reddit.add_subreddit(reddit_subreddit)
	assert subreddits.subreddit_posts_per_hour(reddit, reddit_subreddit.display_name) == 2
