import discord_logging
import prawcore.exceptions

log = discord_logging.get_logger()

import counters
from praw_wrapper.reddit import ReturnType
import utils


def send_queued_notifications(reddit, database, disable_notifications=False):
	count_pending_notifications = database.get_count_pending_notifications()
	counters.queue.set(count_pending_notifications)
	if disable_notifications:
		return 0

	notifications_sent = 0
	if count_pending_notifications > 0:
		users_to_delete = set()
		notifications = database.get_pending_notifications(utils.requests_available(count_pending_notifications))
		for notification in notifications:
			notifications_sent += 1
			counters.notifications.inc()
			counters.queue.dec()
			if notification.submission is None:
				log.warning(f"Notification submission is none: {notification.id}")
			else:
				counters.queue_age.set((utils.datetime_now() - notification.submission.time_created).total_seconds())
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

			submissions = database.get_recent_submissions_for_author(
				notification.submission.author,
				notification.submission.subreddit,
				notification.submission.id,
				3)

			body_bldr = utils.get_footer(notification.render_notification(submissions))
			subject_bldr = notification.render_subject()
			result = reddit.send_message(notification.subscription.subscriber.name, ''.join(subject_bldr), ''.join(body_bldr), retry_seconds=300)
			notification.submission.messages_sent += 1
			if result != ReturnType.SUCCESS:
				counters.api_responses.labels(call='notif', type=result.name.lower()).inc()

			if result in [ReturnType.INVALID_USER, ReturnType.USER_DOESNT_EXIST]:
				log.info(f"User doesn't exist: u/{notification.subscription.subscriber.name}")
				users_to_delete.add(notification.subscription.subscriber)
			elif result in [ReturnType.NOT_WHITELISTED_BY_USER_MESSAGE]:
				log.info(f"User blocked notification message: u/{notification.subscription.subscriber.name}")
			elif result in [ReturnType.PM_MODERATOR_RESTRICTION]:
				log.warning(f"User moderator filter blocked notification message: u/{notification.subscription.subscriber.name}")
			elif result in [ReturnType.SERVER_ERROR]:
				log.warning(f"Failure sending notification message to u/{notification.subscription.subscriber.name}")
				counters.errors.labels(type='api').inc()
			else:
				if notification.subscription.subscriber.first_failure is not None:
					notification.subscription.subscriber.first_failure = None

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
