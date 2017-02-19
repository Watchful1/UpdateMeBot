import praw
import globals
import traceback

reddit = None
log = None
whitelist = None


def init(logger, responseWhitelist, client_id, client_secret, refresh_token):
	global reddit
	global log
	global whitelist

	reddit = praw.Reddit(
		client_id=client_id,
		client_secret=client_secret,
		refresh_token=refresh_token,
		user_agent=globals.USER_AGENT)

	globals.ACCOUNT_NAME = str(reddit.user.me())

	log = logger
	whitelist = responseWhitelist

	log.info("Logged into reddit as /u/"+globals.ACCOUNT_NAME)


def sendMessage(recipient, subject, message):
	if whitelist is not None and recipient not in whitelist:
		return True
	try:
		reddit.redditor(recipient).message(
			subject=subject,
			message=message
		)
		return True
	except Exception as err:
		log.warning(traceback.format_exc())
		return False


def getMessages():
	return reddit.inbox.unread(limit=100)


def markMessageRead(message):
	if whitelist is None:
		message.mark_as_read()


def replyMessage(message, body):
	if whitelist is not None and str(message.author) not in whitelist:
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
		if whitelist is not None and str(parent.author) not in whitelist:
			return None
		resultComment = parent.reply(message)
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