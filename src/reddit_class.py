import discord_logging
import praw
import prawcore
import traceback
import requests
from datetime import timedelta
from datetime import datetime


log = discord_logging.get_logger()


import static
import utils
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

	def quarantine_opt_in(self, subreddit_name):
		log.debug(f"Opting in to subreddit: {subreddit_name}")
		if not self.no_post:
			try:
				self.reddit.subreddit(subreddit_name).quaran.opt_in()
			except Exception:
				log.warning(f"Error opting in to subreddit: {subreddit_name}")
				log.warning(traceback.format_exc())
				return False
		return True

	def get_keyword_comments(self, keyword, last_seen):
		if not len(self.processed_comments.list):
			last_seen = last_seen + timedelta(seconds=1)

		log.debug(f"Fetching comments for keyword: {keyword} : {last_seen.strftime('%Y-%m-%d %H:%M:%S')}")
		url = f"https://api.pushshift.io/reddit/comment/search?q={keyword}&limit=100&sort=desc"
		lag_url = "https://api.pushshift.io/reddit/comment/search?limit=1&sort=desc"
		try:
			response = requests.get(url, headers={'User-Agent': static.USER_AGENT}, timeout=10)
			if response.status_code != 200:
				self.consecutive_timeouts += 1
				if self.consecutive_timeouts >= pow(self.timeout_warn_threshold, 2) * 5:
					log.warning(f"{self.consecutive_timeouts} consecutive timeouts for search term: {keyword}")
					self.timeout_warn_threshold += 1
				return []
			comments = response.json()['data']

			if self.pushshift_lag_checked is None or \
					utils.datetime_now() - timedelta(minutes=10) > self.pushshift_lag_checked:
				log.debug("Updating pushshift comment lag")
				json = requests.get(lag_url, headers={'User-Agent': static.USER_AGENT}, timeout=10)
				if json.status_code == 200:
					comment_created = datetime.utcfromtimestamp(json.json()['data'][0]['created_utc'])
					self.pushshift_lag = round((utils.datetime_now() - comment_created).seconds / 60, 0)
					self.pushshift_lag_checked = utils.datetime_now()

			if self.timeout_warn_threshold > 1:
				log.warning(f"Recovered from timeouts after {self.consecutive_timeouts} attempts")

			self.consecutive_timeouts = 0
			self.timeout_warn_threshold = 1

		except requests.exceptions.ReadTimeout:
			self.consecutive_timeouts += 1
			if self.consecutive_timeouts >= pow(self.timeout_warn_threshold, 2) * 5:
				log.warning(f"{self.consecutive_timeouts} consecutive timeouts for search term: {keyword}")
				self.timeout_warn_threshold += 1
			return []

		except Exception as err:
			log.warning(f"Could not parse data for search term: {keyword}")
			log.warning(traceback.format_exc())
			return []

		if not len(comments):
			log.warning(f"No comments found for search term: {keyword}")
			return []

		result_comments = []
		for comment in comments:
			date_time = datetime.utcfromtimestamp(comment['created_utc'])
			if last_seen > date_time:
				break

			if not self.processed_comments.contains(comment['id']):
				result_comments.append(comment)

		log.debug(f"Found comments: {len(result_comments)}")
		return result_comments

	def mark_keyword_comment_processed(self, comment_id):
		self.processed_comments.put(comment_id)
