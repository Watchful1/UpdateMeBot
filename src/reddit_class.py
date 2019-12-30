import discord_logging
import praw
import prawcore


log = discord_logging.get_logger()


import static
from classes.queue import Queue


class Reddit:
	def __init__(self, user_name, prefix, no_post):
		log.info(f"Initializing reddit class: user={user_name} prefix={prefix} no_post={no_post}")
		self.no_post = no_post

		config = discord_logging.get_config()
		client_id = discord_logging.get_config_var(config, user_name, f"{prefix}_client_id")
		client_secret = discord_logging.get_config_var(config, user_name, f"{prefix}_client_secret")
		refresh_token = discord_logging.get_config_var(config, user_name, f"{prefix}_refresh_token")
		self.reddit = praw.Reddit(
			user_name,
			client_id=client_id,
			client_secret=client_secret,
			refresh_token=refresh_token,
			user_agent=static.USER_AGENT)

		log.info(f"Logged into reddit as /u/{static.ACCOUNT_NAME} {prefix}_")

		self.processed_comments = Queue(100)
		self.consecutive_timeouts = 0
		self.timeout_warn_threshold = 1
		self.pushshift_lag = 0
		self.pushshift_lag_checked = None
