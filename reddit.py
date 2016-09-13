import praw
import OAuth2Util
import globals
import traceback

reddit = None
log = None
whitelist = None


def init(logger, responseWhitelist):
	global reddit
	global log
	global whitelist

	reddit = praw.Reddit(user_agent=globals.USER_AGENT, log_request=0)
	OAuth = OAuth2Util.OAuth2Util(reddit)
	OAuth.refresh(force=True)

	log = logger
	whitelist = responseWhitelist


def sendMessage(recipient, subject, message):
	if whitelist is not None and recipient not in whitelist:
		return True
	try:
		reddit.send_message(
			recipient=recipient,
			subject=subject,
			message=message
		)
		return True
	except Exception as err:
		log.warning(traceback.format_exc())
		return False


def getMessages():
	return reddit.get_unread(unset_has_mail=True, update_user=True, limit=100)


def markMessageRead(message):
	if whitelist is None:
		message.mark_as_read()


def replyMessage(message, body):
	if whitelist is not None and message.author not in whitelist:
		return True
	try:
		message.reply(body)
		return True
	except Exception as err:
		log.warning(traceback.format_exc())
		return False


def getSubmission(id):
	return reddit.get_submission(submission_id=id)


def deleteComment(id=None, comment=None):
	if whitelist is not None and not len(whitelist):
		return True
	try:
		if id is not None:
			reddit.get_info(thing_id='t1_' + id).delete()
		if comment is not None:
			comment.delete()
		return True
	except Exception as err:
		log.warning(traceback.format_exc())
		return False


def replyComment(id, message):
	try:
		parent = reddit.get_info(thing_id='t1_' + id)
		if whitelist is not None and parent.author not in whitelist:
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
		reddit.get_info(thing_id='t1_' + id).edit(message)
		return True
	except Exception as err:
		log.warning(traceback.format_exc())
		return False


def getUserComments(user):
	return reddit.get_redditor(user).get_comments(limit=100)