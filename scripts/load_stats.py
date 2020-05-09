import sqlite3
import os
from datetime import datetime, timedelta
import discord_logging
import time

log = discord_logging.init_logging()

from database import Database
from classes.stat import Stat


new_db = Database()
new_db.session.query(Stat).delete(synchronize_session='fetch')

valid_authors = set()
authors_file_read = open("valid_authors.txt", 'r')
for line in authors_file_read:
	valid_authors.add(line.strip().lower())
authors_file_read.close()

subreddits = {}
for subreddit in new_db.get_all_subreddits():
	subreddits[subreddit.name.lower()] = subreddit

base_folder = r"C:\Users\greg\Desktop\UpdateMeBot"
for filename in reversed(os.listdir(base_folder)):
	#start = time.perf_counter()
	date_time = datetime.strptime(filename, "%Y-%m-%d_%H-%M.db")

	# current_day = date_time.date()
	log.info(date_time.strftime("%Y-%m-%d"))

	#mark1 = time.perf_counter()
	dbConn = sqlite3.connect(base_folder + os.path.sep + filename)
	c = dbConn.cursor()
	# mark2 = time.perf_counter()
	# first_row = True
	# time_adding = 0
	# count_rows = 0
	# count_valid_authors = 0
	# count_valid_subs = 0
	# mark3 = time.perf_counter()
	for row in c.execute('''
				select scrips.Subreddit, scrips.SubscribedTo, count(*) as subscribers
				from subscriptions scrips
					inner join subredditWhitelist subs on subs.Subreddit = scrips.subreddit
				where subs.Status = 1
				group by scrips.Subreddit, scrips.SubscribedTo
				order by subscribers desc
			'''):
		# if first_row:
		# 	first_row = False
		# 	mark3 = time.perf_counter()
		#count_rows += 1
		if row[1] in valid_authors:
			#count_valid_authors += 1
			subreddit = subreddits.get(row[0])
			if subreddit is not None:
				#count_valid_subs += 1
				#add_start = time.perf_counter()
				new_db.add_stat(
					Stat(
						author=new_db.get_or_add_user(row[1]),
						subreddit=subreddit,
						date=date_time.date(),
						count_subscriptions=row[2]
					)
				)
				#time_adding += time.perf_counter() - add_start

	#mark4 = time.perf_counter()
	dbConn.close()
	new_db.commit()
	#mark5 = time.perf_counter()
	#log.info(f"{mark1 - start:.4} : {mark2 - mark1:.4} : {mark3 - mark2:.4} : {mark4 - mark3:.4}|{time_adding:.4}|{count_rows}|{count_valid_authors}|{count_valid_subs} : {mark5 - mark4:.4} : {mark5 - start:.4}")

	# if current_day < datetime.utcnow().date() - timedelta(days=120):
	# 	break

new_db.close()
