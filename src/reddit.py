import configparser
import traceback

import praw

from src import globals

reddit = None
log = None
whitelist = None


def init(logger, responseWhitelist, user):
	global reddit
	global log
	global whitelist

	try:
		reddit = praw.Reddit(
			user,
			user_agent=globals.USER_AGENT)
	except configparser.NoSectionError:
		log.error("User "+user+" not in praw.ini, aborting")
		return False

	globals.ACCOUNT_NAME = str(reddit.user.me())

	log = logger
	whitelist = responseWhitelist

	log.info("Logged into reddit as /u/" + globals.ACCOUNT_NAME)
	return True


def checkConnection():
	try:
		reddit.user.me()
		return True
	except Exception as err:
		return False


def sendMessage(recipient, subject, message):
	if whitelist is not None and recipient.lower() not in whitelist:
		return True
	try:
		reddit.redditor(recipient).message(
			subject=subject,
			message=message
		)
		return True
	except praw.exceptions.APIException as err:
		log.warning("User "+recipient+" doesn't exist")
		return False
	except Exception as err:
		log.warning(traceback.format_exc())
		return False


def getMessages():
	return reddit.inbox.unread(limit=100)


def markMessageRead(message):
	if whitelist is None:
		message.mark_read()


def replyMessage(message, body):
	if whitelist is not None and str(message.author).lower() not in whitelist:
		return True
	try:
		message.reply(body)
		return True
	except Exception as err:
		log.warning(traceback.format_exc())
		return False


def getSubmission(id):
	return reddit.submission(id=id)


def deleteComment(id=None, comment=None):
	if whitelist is not None and not len(whitelist):
		return True
	try:
		if id is not None:
			idComment = reddit.comment(id)
			if str(idComment.author).lower() == globals.ACCOUNT_NAME.lower():
				idComment.delete()
			else:
				log.warning("Skipping comment delete, not author")
		if comment is not None:
			if str(comment.author).lower() == globals.ACCOUNT_NAME.lower():
				comment.delete()
			else:
				log.warning("Skipping comment delete, not author")
		return True
	except Exception as err:
		log.warning(traceback.format_exc())
		return False


def replyComment(id, message):
	try:
		parent = reddit.comment(id)
		if whitelist is not None and str(parent.author).lower() not in whitelist:
			return None
		resultComment = parent.reply(message)
		return resultComment.id
	except Exception as err:
		log.warning(traceback.format_exc())
		return None


def replySubmission(id, message):
	try:
		submission = getSubmission(id)
		if whitelist is not None and str(submission.author).lower() not in whitelist:
			return None
		resultComment = submission.reply(message)
		return resultComment.id
	except Exception as err:
		log.warning(traceback.format_exc())
		return None


def editComment(id, message):
	if whitelist is not None and not len(whitelist):
		return True
	try:
		comment = reddit.comment(id)
		if str(comment.author).lower() == globals.ACCOUNT_NAME.lower():
			comment.edit(message)
			return True
		else:
			log.warning("Skipping comment edit, not author")
			return True
	except Exception as err:
		log.warning(traceback.format_exc())
		return False


def getUserComments(user):
	return reddit.redditor(user).comments.new(limit=100)


def getSubredditSubmissions(subredditName):
	return reddit.subreddit(subredditName).new(limit=1000)


def getComment(id):
	return reddit.comment(id)
