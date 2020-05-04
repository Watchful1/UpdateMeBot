import sqlite3
import praw
import prawcore
import discord_logging

log = discord_logging.init_logging()

import static
import utils
from database import Database

r = praw.Reddit("Watchful1BotTest")

new_db = Database()

dbConn = sqlite3.connect(static.DB_TO_MIGRATE_FROM)
c = dbConn.cursor()
log.info(f"Building valid author list")

count_valid = 0
existing_authors = set()
authors_file_read = open("valid_authors.txt", 'r')
for line in authors_file_read:
	count_valid += 1
	existing_authors.add(line.strip())
authors_file_read.close()

log.info(f"Read in {count_valid} valid existing authors")

count_invalid = 0
authors_file_read = open("invalid_authors.txt", 'r')
for line in authors_file_read:
	count_invalid += 1
	existing_authors.add(line.strip())
authors_file_read.close()

log.info(f"Read in {count_invalid} invalid existing authors")

pending_authors = []
for row in c.execute('''
	SELECT distinct SubscribedTo
	FROM subscriptions
'''):
	author_name = row[0]
	if author_name not in existing_authors:
		pending_authors.append(author_name)
dbConn.close()

log.info(f"Loaded {len(pending_authors)} pending authors")
count_total_authors = count_valid + count_invalid + len(pending_authors)

valid_authors_file_write = open("valid_authors.txt", 'a')
invalid_authors_file_write = open("invalid_authors.txt", 'a')
for author in pending_authors:
	if (count_valid + count_invalid) % 100 == 0:
		log.info(f"{count_valid + count_invalid}/{count_total_authors}")
		valid_authors_file_write.close()
		invalid_authors_file_write.close()
		valid_authors_file_write = open("valid_authors.txt", 'a')
		invalid_authors_file_write = open("invalid_authors.txt", 'a')
	reddit_author = r.redditor(author)
	try:
		reddit_author._fetch()
	except prawcore.exceptions.NotFound:
		invalid_authors_file_write.write(f"{reddit_author.name}\n")
		count_invalid += 1
		continue

	valid_authors_file_write.write(f"{reddit_author.name}\n")
	count_valid += 1

log.info(f"{count_valid + count_invalid}/{count_total_authors}")

valid_authors_file_write.close()
invalid_authors_file_write.close()
