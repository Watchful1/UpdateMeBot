import discord_logging
import sqlalchemy
from datetime import datetime, timedelta
import os

log = discord_logging.init_logging()

from database import Database
from classes.subscription import Subscription
from classes.user import User
import utils

if __name__ == "__main__":
	backup_folder = r"D:\backup\UpdateMeBot"
	username = "Mick8283"
	start_date = datetime.today() - timedelta(days=2000)

	for subdir, dirs, files in os.walk(backup_folder):
		for filename in files:
			if filename.endswith(".db"):
				input_path = os.path.join(subdir, filename)
				try:
					backup_date = datetime.strptime(filename[:-3], "%Y-%m-%d_%H-%M")
					if backup_date < start_date:
						continue

					database = Database(override_path=input_path, quiet=True)
					subscriptions = database.get_user_subscriptions_by_name(username)
					log.info(f"{backup_date}: {len(subscriptions)}")
					database.close()
				except (ValueError, sqlalchemy.exc.OperationalError, sqlalchemy.exc.DatabaseError):
					continue
