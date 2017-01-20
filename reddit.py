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
	if whitelist is not None and str(message.author) not in whitelist:
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
			idComment = reddit.get_info(thing_id='t1_' + id)
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
		parent = reddit.get_info(thing_id='t1_' + id)
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
		comment = reddit.get_info(thing_id='t1_' + id)
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
	return reddit.get_redditor(user).get_comments(limit=100)