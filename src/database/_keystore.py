import discord_logging

import utils
from classes.key_value import KeyValue

log = discord_logging.get_logger()


class _DatabaseKeystore:
	def __init__(self):
		self.session = self.session  # for pycharm linting

	def save_keystore(self, key, value):
		log.debug(f"Saving keystore: {key} : {value}")
		self.session.merge(KeyValue(key, value))

	def get_keystore(self, key):
		log.debug(f"Fetching keystore: {key}")
		key_value = self.session.query(KeyValue).filter_by(key=key).first()

		if key_value is None:
			log.debug("Key not found")
			return None

		log.debug(f"Value: {key_value.value}")
		return key_value.value

	def save_datetime(self, key, date_time):
		self.save_keystore(key, utils.get_datetime_string(date_time))

	def get_datetime(self, key, is_date=False):
		result = self.get_keystore(key)
		if result is None:
			return None
		else:
			result_date = utils.parse_datetime_string(result)
			if is_date:
				return result_date.date()
			else:
				return result_date

	def get_or_init_datetime(self, key):
		result = self.get_datetime(key)
		if result is None:
			log.warning(f"Initializing key {key} to now")
			now = utils.datetime_now()
			self.save_datetime(key, now)
			return now
		return result
