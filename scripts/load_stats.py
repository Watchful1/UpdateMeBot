import sqlite3
import os
from datetime import datetime
from collections import defaultdict
import discord_logging

log = discord_logging.init_logging()

base_folder = r"C:\Users\greg\Desktop\UpdateMeBot"

current_day = -1
for filename in reversed(os.listdir(base_folder)):
	date_time = datetime.strptime(filename, "%Y-%m-%d_%H-%M.db")
	if date_time.day == current_day:
		continue

	current_day = date_time.day
	log.info(date_time.strftime("%Y-%m-%d"))

	subscribers = 0

	dbConn = sqlite3.connect(base_folder + os.path.sep + filename)
	c = dbConn.cursor()
	counts = defaultdict(lambda: defaultdict(int))
	for row in c.execute('''
				select Subreddit, SubscribedTo, count(*) as subscribers
				from subscriptions
				group by Subreddit, SubscribedTo
				order by subscribers desc
			'''):
		counts[row[0]][row[1]] += row[2]
		subscribers += row[2]

	log.info(str(subscribers))

	dbConn.close()
