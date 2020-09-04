import discord_logging
import traceback

discord_logging.init_logging(debug=True)

from database import Database
import praw_wrapper
import utils
import subreddits

reddit = praw_wrapper.Reddit("Watchful1BotTest", True)

database = Database(log_debug=False)
try:
	subreddits.scan_subreddits(reddit, database)
except Exception as err:
	utils.process_error(f"Error scanning subreddits", err, traceback.format_exc())
