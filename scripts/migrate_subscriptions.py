import sqlite3
import discord_logging

log = discord_logging.init_logging()

import static
from database import Database
from classes.subscription import Subscription

new_db = Database()
new_db.session.query(Subscription).delete(synchronize_session='fetch')

valid_authors = set()
authors_file_read = open("valid_authors.txt", 'r')
for line in authors_file_read:
	valid_authors.add(line.strip().lower())
authors_file_read.close()

subreddits = {}
for subreddit in new_db.get_all_subreddits():
	subreddits[subreddit.name.lower()] = subreddit

user_map = {}

count_subscriptions = 0
invalid_subscriptions_file_write = open("invalid_subscriptions.txt", 'w')
dbConn = sqlite3.connect(static.DB_TO_MIGRATE_FROM)
c = dbConn.cursor()
log.info(f"Starting subscriptions")
for row in c.execute('''
	select Subscriber, SubscribedTo, Subreddit, Single
	from subscriptions
'''):
	if row[1] in valid_authors or row[1] == 'sub':
		subreddit = subreddits.get(row[2])
		if subreddit is not None:
			subscriber = user_map.get(row[0])
			if subscriber is None:
				subscriber = new_db.get_or_add_user(row[0])
				user_map[row[0]] = subscriber
			if row[1] == 'sub':
				author = None
			else:
				author = user_map.get(row[1])
				if author is None:
					author = new_db.get_or_add_user(row[1])
					user_map[row[1]] = author
			subscription = Subscription(
				subscriber=subscriber,
				author=author,
				subreddit=subreddit,
				recurring=not row[3]
			)
			new_db.add_subscription(subscription)
		else:
			try:
				invalid_subscriptions_file_write.write(f"sub: r/{row[2]} u/{row[1]} u/{row[0]} : {row[3]}\n")
			except Exception:
				pass
	else:
		try:
			invalid_subscriptions_file_write.write(f"user: r/{row[2]} u/{row[1]} u/{row[0]} : {row[3]}\n")
		except Exception:
			pass

	count_subscriptions += 1
	if count_subscriptions % 1000 == 0:
		log.info(f"Added {count_subscriptions} subscriptions")
		new_db.commit()

log.info(f"Finished adding {count_subscriptions} subscriptions")

dbConn.close()
new_db.close()
invalid_subscriptions_file_write.close()
