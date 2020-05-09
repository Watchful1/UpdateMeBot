import discord_logging

log = discord_logging.init_logging()

from database import Database

new_db = Database(publish=True)
new_db.close()
