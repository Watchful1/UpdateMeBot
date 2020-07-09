import discord_logging

log = discord_logging.get_logger()

from praw_wrapper import ReturnType
import utils


def send_queued_notifications(reddit, database, counters=None):
	count_pending_notifications = database.get_count_pending_notifications()
	if counters is not None:
		counters.queue_size.set(count_pending_notifications)

	notifications_sent = 0
	if count_pending_notifications > 0:
		users_to_delete = set()
		notifications = database.get_pending_notifications(utils.requests_available(count_pending_notifications))
		for notification in notifications:
			notifications_sent += 1
			if counters is not None:
				counters.notifications_sent.inc()
				counters.queue_size.dec()
			if notification.subscription is None:
				log.warning(
					f"Notification for u/{notification.submission.author.name} in r/"
					f"{notification.submission.subreddit.name} missing subscription, skipping: "
					f"{notification.submission.submission_id}")
				database.delete_notification(notification)
				continue

			log.info(
				f"{notifications_sent}/{len(notifications)}/{count_pending_notifications}: Notifying u/"
				f"{notification.subscription.subscriber.name} for u/{notification.submission.author.name} in r/"
				f"{notification.subscription.subreddit.name} : {notification.submission.submission_id}")

			bldr = utils.get_footer(notification.render_notification())
			result = reddit.send_message(notification.subscription.subscriber.name, "UpdateMeBot Here!", ''.join(bldr))
			notification.submission.messages_sent += 1
			if result in [ReturnType.INVALID_USER, ReturnType.USER_DOESNT_EXIST]:
				log.info(f"User doesn't exist: u/{notification.subscription.subscriber.name}")
				users_to_delete.add(notification.subscription.subscriber)
			if result in [ReturnType.NOT_WHITELISTED_BY_USER_MESSAGE]:
				log.info(f"User blocked notification message: u/{notification.subscription.subscriber.name}")

			if not notification.subscription.recurring:
				log.debug(f"{notification.subscription.id} deleted")
				database.delete_subscription(notification.subscription)

			database.delete_notification(notification)

			if notifications_sent % 50 == 0:
				database.commit()

		database.commit()
		if len(users_to_delete):
			for user in users_to_delete:
				database.purge_user(user)
			database.commit()

	else:
		log.debug("No notifications to send")

	return notifications_sent
