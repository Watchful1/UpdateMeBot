import sqlite3
import discord_logging
from datetime import datetime

log = discord_logging.init_logging()

import static
from database import Database
from classes.key_value import KeyValue

new_db = Database()
new_db.session.query(KeyValue).delete(synchronize_session='fetch')

dbConn = sqlite3.connect(static.DB_TO_MIGRATE_FROM)
c = dbConn.cursor()
log.info(f"Starting comment timestamps")

latest_datetime = None
for row in c.execute('''
	SELECT Timestamp
	FROM commentSearch
'''):
	current_datetime = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
	if latest_datetime is None or current_datetime > latest_datetime:
		latest_datetime = current_datetime

new_db.save_datetime("comment_timestamp", latest_datetime)

log.info(f"Finished migrating comment timestamps")

dbConn.close()
new_db.close()
