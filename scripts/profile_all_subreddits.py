import discord_logging

log = discord_logging.get_logger(init=True)

from database import Database
import subreddits
import reddit_class

reddit = reddit_class.Reddit('Watchful1BotTest', None, False)
new_db = Database()

subreddits.profile_subreddits(new_db, reddit)
