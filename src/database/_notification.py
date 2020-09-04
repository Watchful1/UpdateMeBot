import discord_logging

from classes.notification import Notification
from classes.subscription import Subscription

log = discord_logging.get_logger()


class _DatabaseNotification:
	def __init__(self):
		self.session = self.session  # for pycharm linting
		self.log_debug = self.log_debug

	def add_notification(self, notification):
		if self.log_debug:
			log.debug("Saving new notification")
		self.session.add(notification)

	def get_count_pending_notifications(self):
		if self.log_debug:
			log.debug(f"Fetching count of pending notifications")

		count = self.session.query(Notification)\
			.order_by(Notification.id)\
			.count()

		return count

	def get_pending_notifications(self, count=9999):
		if self.log_debug:
			log.debug(f"Fetching pending notifications")

		notifications = self.session.query(Notification)\
			.order_by(Notification.id)\
			.limit(count)\
			.all()

		return notifications

	def clear_all_notifications(self):
		if self.log_debug:
			log.debug(f"Clearing all notifications in queue")

		self.session.query(Notification)\
			.delete(synchronize_session='fetch')

	def delete_notifications_for_subscription(self, subscription):
		if self.log_debug:
			log.debug(f"Deleting notifications for {subscription}")

		return self.session.query(Notification)\
			.filter(Notification.subscription == subscription)\
			.delete(synchronize_session='fetch')

	def delete_notification(self, notification):
		if self.log_debug:
			log.debug(f"Deleting notification by id: {notification.id}")
		self.session.delete(notification)
