import discord_logging

log = discord_logging.get_logger(init=True)

from database import Database
import subreddits
import praw_wrapper

reddit = praw_wrapper.Reddit('Watchful1BotTest', False)
database = Database()

subreddits.profile_subreddits(reddit, database, limit=9999)
