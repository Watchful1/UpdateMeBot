import praw
import OAuth2Util
import globals
import traceback

reddit = None
log = None


def init(logger):
	global reddit
	global log

	reddit = praw.Reddit(user_agent=globals.USER_AGENT, log_request=0)
	OAuth = OAuth2Util.OAuth2Util(reddit)
	OAuth.refresh(force=True)

	log = logger


def sendMessage(recipient, subject, message):
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
	message.mark_as_read()


def replyMessage(message, body):
	try:
		message.reply(body)
		return True
	except Exception as err:
		log.warning(traceback.format_exc())
		return False


def getSubmission(id):
	return reddit.get_submission(submission_id=id)


def deleteComment(id=None, comment=None):
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
		resultComment = reddit.get_info(thing_id='t1_' + id).reply(message)
		return resultComment.id
	except Exception as err:
		log.warning(traceback.format_exc())
		return None


def editComment(id, message):
	try:
		reddit.get_info(thing_id='t1_' + id).edit(message)
		return True
	except Exception as err:
		log.warning(traceback.format_exc())
		return False


def getUserComments(user):
	return reddit.get_redditor(user).get_comments(limit=100)