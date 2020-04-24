import discord_logging


log = discord_logging.get_logger()


from classes.enums import ReturnType
import utils


def send_queued_notifications(reddit, database):
	count_pending_notifications = database.get_count_pending_notifications()

	notifications_sent = 0
	if count_pending_notifications > 0:
		notifications = database.get_pending_notifications(utils.requests_available(count_pending_notifications))
		for notification in notifications:
			notifications_sent += 1
			log.info(
				f"{notifications_sent}/{len(notifications)}/{count_pending_notifications}: Notifying u/"
				f"{notification.subscription.subscriber.name} for u/{notification.subscription.author.name} in r/"
				f"{notification.subscription.subreddit.name} : {notification.submission.submission_id}")

			bldr = utils.get_footer(notification.render_notification())
			result = reddit.send_message(notification.subscription.subscriber.name, "UpdateMeBot Here!", ''.join(bldr))
			notification.submission.messages_sent += 1
			if result in (ReturnType.INVALID_USER, ReturnType.USER_DOESNT_EXIST):
				log.info(f"User doesn't exist: u/{notification.subscription.subscriber.name}")

			if not notification.subscription.recurring:
				log.debug(f"{notification.subscription.id} deleted")
				database.delete_subscription(notification.subscription)

			database.delete_notification(notification)

		database.commit()

	else:
		log.debug("No notifications to send")

	return notifications_sent
