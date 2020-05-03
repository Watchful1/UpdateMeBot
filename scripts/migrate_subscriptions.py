import sqlite3
import discord_logging

log = discord_logging.init_logging()

import static
from database import Database
from classes.subscription import Subscription

new_db = Database()
new_db.session.query(Subscription).delete(synchronize_session='fetch')

count_subscriptions = 0

dbConn = sqlite3.connect(static.DB_TO_MIGRATE_FROM)
c = dbConn.cursor()
log.info(f"Starting subscriptions")
for row in c.execute('''
	select Subscriber, SubscribedTo, Subreddit, Single
	from subscriptions
'''):
	subscriber = new_db.get_or_add_user(row[0])
	author = new_db.get_or_add_user(row[1])
	subreddit = new_db.get_or_add_subreddit(row[2])
	subscription = Subscription(
		subscriber=subscriber,
		author=author,
		subreddit=subreddit,
		recurring=not row[3]
	)
	new_db.add_subscription(subscription)

	count_subscriptions += 1
	if count_subscriptions % 1000 == 0:
		log.info(f"Added {count_subscriptions} subscriptions")
		new_db.commit()

log.info(f"Finished adding {count_subscriptions} subscriptions")

dbConn.close()
new_db.close()
