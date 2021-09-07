import discord_logging
import sys

log = discord_logging.init_logging(backup_count=20)

from database import Database

database = Database()

username = sys.argv[1]
source_subreddit = sys.argv[2]
dest_subreddit = sys.argv[3]

db_user = database.get_user(username)
if db_user is None:
	log.info(f"u/{username} doesn't exist, exiting")
	sys.exit()

db_source_subreddit = database.get_subreddit(source_subreddit)
if db_source_subreddit is None:
	log.info(f"r/{source_subreddit} doesn't exist, exiting")
	sys.exit()

db_dest_subreddit = database.get_subreddit(dest_subreddit)
if db_dest_subreddit is None:
	log.info(f"r/{dest_subreddit} doesn't exist, creating")
	db_dest_subreddit = database.get_or_add_subreddit(
		dest_subreddit,
		case_is_user_supplied=True,
		enable_subreddit_if_new=True)

subscriptions = database.get_subscriptions_for_author_subreddit(db_user, db_source_subreddit)
log.info(f"Moving {len(subscriptions)} for u/{username} from r/{source_subreddit} to r/{dest_subreddit}")
for subscription in subscriptions:
	subscription.subreddit = db_dest_subreddit

database.close()

