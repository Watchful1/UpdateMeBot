import discord_logging

log = discord_logging.init_logging()

import static
from database import Database
from classes.stat import Stat

database = Database()

# delete stats under 10
log.info(f"Cleaning up stats")

stats_total = database.session.query(Stat).count()
stats_deleted = database.session.query(Stat).filter(Stat.count_subscriptions < 10).delete(synchronize_session='fetch')
stats_remaining = database.session.query(Stat).count()

log.info(f"Deleted {stats_deleted:,} of {stats_total:,} stats")
log.info(f"{stats_deleted:,} + {stats_remaining:,} = {stats_deleted + stats_remaining:,} : {stats_deleted + stats_remaining == stats_total}")

database.commit()
database.session.execute("VACUUM")
database.commit()

subreddits_to_blacklist = ['WritingPrompts', 'AskReddit', 'whatisthisthing', 'bestoflegaladvice', 'AskHistorians', 'RequestABot']
subreddits_to_delete = ['subreddit', 'RequestABot', 'Overwatch', 'amistories', 'Darkland', 'John_writes', 'jsgunn', 'SubTestBot2', 'TwentyNinetyNine', 'EdgarAllanHobo', 'GigaWrites', 'pirates']
subreddits_to_activate = ['IsTodayFridayThe13th', 'ProRevenge', 'imsorryjon', 'whatisthisthing', 'JUSTNOMIL', 'entitledparents', 'redditserials', 'eroticliterature']
users_to_delete = ['nosleepautobot']

database.close()
