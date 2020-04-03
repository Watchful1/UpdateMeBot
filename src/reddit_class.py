import discord_logging
import praw
import prawcore
import traceback


log = discord_logging.get_logger()


import static
from classes.queue import Queue
from classes.enums import ReturnType


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

	def run_function(self, function, arguments):
		output = None
		result = None
		try:
			output = function(*arguments)
		except praw.exceptions.APIException as err:
			for return_type in ReturnType:
				if err.error_type == return_type.name:
					result = return_type
					break
			if result is None:
				raise
		except prawcore.exceptions.Forbidden:
			result = ReturnType.FORBIDDEN
		except IndexError:
			result = ReturnType.QUARANTINED

		if result is None:
			result = ReturnType.SUCCESS
		return output, result

	def is_message(self, item):
		return isinstance(item, praw.models.Message)

	def get_messages(self, count=500):
		log.debug("Fetching unread messages")
		message_list = []
		for message in self.reddit.inbox.unread(limit=count):
			message_list.append(message)
		return message_list

	def reply_message(self, message, body):
		log.debug(f"Replying to message: {message.id}")
		if self.no_post:
			log.info(body)
			return ReturnType.SUCCESS
		else:
			output, result = self.run_function(message.reply, [body])
			return result

	def mark_read(self, message):
		log.debug(f"Marking message as read: {message.id}")
		if not self.no_post:
			message.mark_read()

	def get_submission(self, submission_id):
		log.debug(f"Fetching submission by id: {submission_id}")
		if submission_id == "xxxxxx":
			return None
		else:
			return self.reddit.submission(submission_id)

	def get_comment(self, comment_id):
		log.debug(f"Fetching comment by id: {comment_id}")
		if comment_id == "xxxxxx":
			return None
		else:
			return self.reddit.comment(comment_id)

	def edit_comment(self, body, comment=None, comment_id=None):
		if comment is None:
			comment = self.get_comment(comment_id)
		log.debug(f"Editing comment: {comment.id}")

		if self.no_post:
			log.info(body)
		else:
			output, result = self.run_function(comment.edit, [body])
			return result

	def delete_comment(self, comment):
		log.debug(f"Deleting comment: {comment.id}")
		if not self.no_post:
			try:
				comment.delete()
			except Exception:
				log.warning(f"Error deleting comment: {comment.comment_id}")
				log.warning(traceback.format_exc())
				return False
		return True

	def get_subreddit_submissions(self, subreddit_name):
		log.debug(f"Getting subreddit submissions: {subreddit_name}")
		return self.reddit.subreddit(subreddit_name).new(limit=1000)
