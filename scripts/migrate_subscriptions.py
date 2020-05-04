import sqlite3
import discord_logging

log = discord_logging.init_logging()

import static
from database import Database
from classes.subscription import Subscription

new_db = Database()

valid_authors = set()
authors_file_read = open("valid_authors.txt", 'r')
for line in authors_file_read:
	valid_authors.add(line.strip())
authors_file_read.close()

count_subscriptions = 0

invalid_subscriptions_file_write = open("invalid_subscriptions.txt", 'w')
dbConn = sqlite3.connect(static.DB_TO_MIGRATE_FROM)
c = dbConn.cursor()
log.info(f"Starting subscriptions")
for row in c.execute('''
	select Subscriber, SubscribedTo, Subreddit, Single
	from subscriptions
'''):
	if row[1] in valid_authors:
		subreddit = new_db.get_subreddit(row[2])
		if subreddit is not None:
			subscriber = new_db.get_or_add_user(row[0])
			author = new_db.get_or_add_user(row[1])
			subscription = Subscription(
				subscriber=subscriber,
				author=author,
				subreddit=subreddit,
				recurring=not row[3]
			)
			new_db.add_subscription(subscription)
		else:
			invalid_subscriptions_file_write.write(f"sub: r/{row[2]} u/{row[1]} u/{row[0]} : {row[3]}\n")
	else:
		invalid_subscriptions_file_write.write(f"user: r/{row[2]} u/{row[1]} u/{row[0]} : {row[3]}\n")

	count_subscriptions += 1
	if count_subscriptions % 1000 == 0:
		log.info(f"Added {count_subscriptions} subscriptions")
		new_db.commit()

log.info(f"Finished adding {count_subscriptions} subscriptions")

dbConn.close()
new_db.close()
invalid_subscriptions_file_write.close()
