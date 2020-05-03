import sqlite3
import discord_logging
from datetime import datetime

log = discord_logging.init_logging()

import static
from database import Database

new_db = Database()

count_subreddits = 0

dbConn = sqlite3.connect(static.DB_TO_MIGRATE_FROM)
c = dbConn.cursor()
log.info(f"Starting scan times")
for row in c.execute('''
	select s.Subreddit, s.LastChecked
	from subscriptions s
		inner join subredditWhitelist sW on s.Subreddit = sW.Subreddit
	where s.Subreddit != ''
		and sW.Status = 1
	group by s.Subreddit, s.LastChecked
'''):
	subreddit = new_db.get_or_add_subreddit(row[0])
	if row[0] == "relationships":
		log.info(row[1])
	scan_datetime = datetime.strptime(row[1], "%Y-%m-%d %H:%M:%S").replace(microsecond=0)
	subreddit.last_scanned = scan_datetime

	count_subreddits += 1
	if count_subreddits % 100 == 0:
		log.info(f"Added {count_subreddits} scan times")
		new_db.commit()

log.info(f"Finished adding scan times for {count_subreddits} subreddits")

dbConn.close()
new_db.close()
