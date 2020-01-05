from datetime import datetime
import discord_logging


log = discord_logging.get_logger()


def datetime_now():
	return datetime.utcnow().replace(microsecond=0)
