from datetime import datetime, timedelta
import discord_logging

log = discord_logging.init_logging()

from database import Database
from classes.stat import Stat


new_db = Database()

current_date = datetime(2016, 8, 27).date()
now_date = datetime.utcnow().date()

previous_stats = []
while current_date < now_date:
	current_stats = new_db.get_all_stats_for_day(current_date)
	if not current_stats:
		log.info(f"Extrapolating for {current_date.strftime('%Y-%m-%d')}")

		for stat in previous_stats:
			new_db.add_stat(
				Stat(
					author=stat.author,
					subreddit=stat.subreddit,
					date=current_date,
					count_subscriptions=stat.count_subscriptions
				)
			)

		new_db.commit()

	current_date += timedelta(days=1)

new_db.close()
