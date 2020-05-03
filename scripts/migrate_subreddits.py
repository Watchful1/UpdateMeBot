import sqlite3
import praw
import prawcore
import discord_logging

log = discord_logging.init_logging()

import static
from database import Database
from classes.subreddit import Subreddit
from classes.enums import SubredditPromptType

r = praw.Reddit("Watchful1BotTest")

new_db = Database()

count_subreddits = 0

dbConn = sqlite3.connect(static.DB_TO_MIGRATE_FROM)
c = dbConn.cursor()
log.info(f"Starting subreddits")

for row in c.execute('''
	SELECT Subreddit, Status, DefaultSubscribe, NextNotice, AlwaysPM, Filter, PostsPerDay, LastProfiled
	FROM subredditWhitelist
'''):
	subreddit_name = row[0]
	reddit_subreddit = r.subreddit(subreddit_name)
	try:
		reddit_subreddit._fetch()
	except (prawcore.exceptions.Redirect, prawcore.exceptions.NotFound):
		log.info(f"Subreddit r/{subreddit_name} doesn't exist")
		continue
	except prawcore.exceptions.Forbidden:
		log.info(f"Subreddit r/{subreddit_name} forbidden")
		continue
	subreddit = new_db.get_or_add_subreddit(reddit_subreddit.display_name)
	subreddit.is_enabled = row[1] == 1
	subreddit.default_recurring = row[2]
	subreddit.no_comment = row[4]
	if subreddit_name == 'hfy':
		subreddit.flair_blacklist = 'meta,wp,video,misc,text'
		subreddit.prompt_type = SubredditPromptType.ALL
	elif subreddit_name == 'written4reddit':
		subreddit.prompt_type = SubredditPromptType.ALLOWED
		subreddit.prompt_users.append(new_db.get_or_add_user("written4reddit"))
	elif subreddit_name == 'luna_lovewell':
		subreddit.prompt_type = SubredditPromptType.ALLOWED
		subreddit.prompt_users.append(new_db.get_or_add_user("luna_lovewell"))
	elif subreddit_name == 'luna_lovewell':
		subreddit.prompt_type = SubredditPromptType.ALLOWED
		subreddit.prompt_users.append(new_db.get_or_add_user("luna_lovewell"))

	count_subreddits += 1
	if count_subreddits % 100 == 0:
		log.info(f"Added {count_subreddits} subreddits")
	new_db.commit()

log.info(f"Finished adding {count_subreddits} subreddits")

dbConn.close()
new_db.close()
