import discord_logging
from datetime import timezone

import static
import utils
from classes.enums import ReturnType

log = discord_logging.get_logger()


class User:
	def __init__(self, name, created_utc=None):
		self.name = name
		self.created_utc = created_utc


class Subreddit:
	def __init__(self, name):
		self.display_name = name
		self.posts = []
		self.is_banned = False


class RedditObject:
	def __init__(
		self,
		body=None,
		author=None,
		created=None,
		id=None,
		permalink=None,
		link_id=None,
		prefix="t4",
		subreddit=None,
		dest=None
	):
		self.body = body
		if isinstance(author, User):
			self.author = author
		else:
			self.author = User(author)
		if isinstance(dest, User):
			self.dest = dest
		else:
			self.dest = User(dest)
		if subreddit is None:
			self.subreddit = None
		elif isinstance(subreddit, Subreddit):
			self.subreddit = subreddit
		else:
			self.subreddit = Subreddit(subreddit)
		if id is None:
			self.id = utils.random_id()
		else:
			self.id = id
		self.fullname = f"{prefix}_{self.id}"
		if created is None:
			self.created_utc = utils.datetime_now().replace(tzinfo=timezone.utc).timestamp()
		else:
			self.created_utc = created.replace(tzinfo=timezone.utc).timestamp()
		if permalink is None and self.subreddit is not None:
			permalink = f"/r/{self.subreddit.display_name}/comments/{self.id}"

		if permalink is not None:
			self.permalink = permalink
			self.url = "http://www.reddit.com"+permalink
		self.link_id = link_id

		self.parent = None
		self.children = []

	def get_pushshift_dict(self):
		return {
			'id': self.id,
			'author': self.author.name,
			'link_id': self.link_id,
			'body': self.body,
			'permalink': self.permalink,
			'created_utc': self.created_utc,
			'subreddit': self.subreddit.display_name
		}

	def get_first_child(self):
		if len(self.children):
			return self.children[0]
		else:
			return None

	def get_last_child(self):
		if len(self.children):
			return self.children[-1]
		else:
			return None

	def mark_read(self):
		return

	def reply(self, body):
		new_message = RedditObject(body, static.ACCOUNT_NAME)
		new_message.parent = self
		self.children.append(new_message)
		return new_message


class Reddit:
	def __init__(self, user):
		static.ACCOUNT_NAME = user
		self.sent_messages = []
		self.self_comments = []
		self.all_comments = {}
		self.all_submissions = {}
		self.users = {}
		self.locked_threads = set()
		self.pushshift_lag = 0
		self.subreddits = {}

	def add_comment(self, comment, self_comment=False):
		self.all_comments[comment.id] = comment
		if self_comment:
			self.self_comments.append(comment)

	def add_submission(self, submission):
		self.all_submissions[submission.id] = submission

	def reply_message(self, message, body):
		self.sent_messages.append(message.reply(body))
		return ReturnType.SUCCESS

	def reply_comment(self, comment, body):
		if comment.subreddit is not None and comment.subreddit in self.subreddits and \
				self.subreddits[comment.subreddit].is_banned:
			return None, ReturnType.FORBIDDEN
		elif comment.link_id is not None and utils.id_from_fullname(comment.link_id) in self.locked_threads:
			return None, ReturnType.THREAD_LOCKED
		elif comment.id not in self.all_comments:
			return None, ReturnType.DELETED_COMMENT
		else:
			new_comment = comment.reply(body)
			self.add_comment(new_comment, True)
			return new_comment.id, ReturnType.SUCCESS

	def mark_read(self, message):
		message.mark_read()

	def send_message(self, username, subject, body):
		new_message = RedditObject(body, static.ACCOUNT_NAME, dest=username)
		self.sent_messages.append(new_message)
		return ReturnType.SUCCESS

	def get_comment(self, comment_id):
		if comment_id in self.all_comments:
			return self.all_comments[comment_id]
		else:
			return RedditObject(id=comment_id)

	def get_submission(self, submission_id):
		if submission_id in self.all_submissions:
			return self.all_submissions[submission_id]
		else:
			return None

	def edit_comment(self, body, comment=None, comment_id=None):
		if comment is None:
			comment = self.get_comment(comment_id)

		comment.body = body
		return ReturnType.SUCCESS

	def delete_comment(self, comment):
		if comment.id in self.all_comments:
			del self.all_comments[comment.id]
		try:
			self.self_comments.remove(comment)
		except ValueError:
			pass

		if comment.parent is not None:
			try:
				comment.parent.children.remove(comment)
			except ValueError:
				pass

		for child in comment.children:
			child.parent = None

		return True

	def add_subreddit(self, subreddit):
		self.subreddits[subreddit.display_name] = subreddit

	def ban_subreddit(self, subreddit_name):
		if subreddit_name not in self.subreddits:
			self.subreddits[subreddit_name] = Subreddit(subreddit_name)
		self.subreddits[subreddit_name].is_banned = True

	def lock_thread(self, thread_id):
		self.locked_threads.add(thread_id)

	def get_subreddit_submissions(self, subreddit_names):
		posts = []
		for subreddit_name in subreddit_names.split("+"):
			posts.extend(self.subreddits[subreddit_name].posts)

		return reversed(sorted(posts, key=lambda post: post.created_utc))
