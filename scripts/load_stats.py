import sqlite3
import os
from datetime import datetime, timedelta
import discord_logging

log = discord_logging.init_logging()

from database import Database
from classes.stat import Stat


new_db = Database()
new_db.session.query(Stat).delete(synchronize_session='fetch')

valid_authors = set()
authors_file_read = open("valid_authors.txt", 'r')
for line in authors_file_read:
	valid_authors.add(line.strip())
authors_file_read.close()

base_folder = r"C:\Users\greg\Desktop\UpdateMeBot"
current_day = datetime.utcnow().date()
for filename in reversed(os.listdir(base_folder)):
	date_time = datetime.strptime(filename, "%Y-%m-%d_%H-%M.db")
	if date_time.date() == current_day:
		continue

	current_day = date_time.date()
	log.info(date_time.strftime("%Y-%m-%d"))

	dbConn = sqlite3.connect(base_folder + os.path.sep + filename)
	c = dbConn.cursor()
	for row in c.execute('''
				select scrips.Subreddit, scrips.SubscribedTo, count(*) as subscribers
				from subscriptions scrips
					inner join subredditWhitelist subs on subs.Subreddit = scrips.subreddit
				where subs.Status = 1
				group by scrips.Subreddit, scrips.SubscribedTo
				order by subscribers desc
			'''):
		if row[1] in valid_authors:
			subreddit = new_db.get_subreddit(row[2])
			if subreddit is not None:
				new_db.add_stat(
					Stat(
						author=new_db.get_or_add_user(row[1]),
						subreddit=subreddit,
						date=date_time.date(),
						count_subscriptions=row[2]
					)
				)

	dbConn.close()
	new_db.commit()

	if current_day < datetime.utcnow().date() - timedelta(days=10):
		break

new_db.close()
