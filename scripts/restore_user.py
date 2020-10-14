import discord_logging
import traceback

log = discord_logging.init_logging()

from database import Database
import utils
import subreddits


database = Database(override_path=r"D:\backup\UpdateMeBot\2020-10-01_12-10.db")
user = database.get_user("Rapdactyl")
if user is None:
	log.info("User doesn't exist")
else:
	for subscription in database.get_user_subscriptions(user):
		log.info(subscription)
