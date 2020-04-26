import sqlite3
import os
from datetime import datetime
import discord_logging

log = discord_logging.init_logging()

from database import Database
from classes.stat import Stat


new_db = Database(debug=True, publish=True)

base_folder = r"C:\Users\greg\Desktop\UpdateMeBot"

current_day = -1
count_days = 0
for filename in reversed(os.listdir(base_folder)):
	date_time = datetime.strptime(filename, "%Y-%m-%d_%H-%M.db")
	if date_time.day == current_day:
		continue

	current_day = date_time.day
	log.info(date_time.strftime("%Y-%m-%d"))

	dbConn = sqlite3.connect(base_folder + os.path.sep + filename)
	c = dbConn.cursor()
	for row in c.execute('''
				select Subreddit, SubscribedTo, count(*) as subscribers
				from subscriptions
				group by Subreddit, SubscribedTo
				order by subscribers desc
			'''):
		new_db.add_stat(
			Stat(
				author=new_db.get_or_add_user(row[1]),
				subreddit=new_db.get_or_add_subreddit(row[0]),
				date=date_time.date(),
				count_subscriptions=row[2]
			)
		)

	dbConn.close()

	count_days += 1
	# if count_days >= 3:
	# 	break

# for stat in new_db.get_recent_stats_for_author_subreddit(
# 		new_db.get_or_add_user("hyperobscura"),
# 		new_db.get_or_add_subreddit("nosleep")
# ):
# 	log.info(stat)
