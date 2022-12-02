import discord_logging
import argparse

log = discord_logging.init_logging(backup_count=20)

from database import Database
from classes.subscription import Subscription

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Copy subscriptions from backup file")
	parser.add_argument("user", help="The username to copy")
	parser.add_argument("backup", help="The location of the backup file")
	args = parser.parse_args()

	main_database = Database()
	log.info(f"Opening backup {args.backup}")
	backup_database = Database(override_path=args.backup)

	backup_subs = backup_database.get_user_subscriptions_by_name(args.user, only_enabled=False)
	log.info(f"Copying {len(backup_subs)} from {args.backup} for u/{args.user}")

	main_subs_count = len(main_database.get_user_subscriptions_by_name(args.user, only_enabled=False))
	log.info(f"User has {main_subs_count} in main")

	for backup_sub in backup_subs:
		subscriber = main_database.get_or_add_user(backup_sub.subscriber.name)
		author = main_database.get_or_add_user(backup_sub.author.name)
		subreddit = main_database.get_or_add_subreddit(backup_sub.subreddit.name)
		result_message, subscription = Subscription.create_update_subscription(
			main_database, subscriber, author, subreddit, backup_sub.recurring, backup_sub.tag
		)

	main_database.commit()
	main_subs_count = len(main_database.get_user_subscriptions_by_name(args.user, only_enabled=False))
	log.info(f"User has {main_subs_count} in main")
	main_database.close()
	backup_database.close()
