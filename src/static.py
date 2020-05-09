USER_AGENT = "RemindMeBot (by /u/Watchful1)"
OWNER = "Watchful1"
ACCOUNT_NAME = "Watchful1BotTest"
DATABASE_NAME = "database.db"
BACKUP_FOLDER_NAME = "backup"
BLACKLISTED_ACCOUNTS = ['[deleted]', 'AutoModerator']

TRIGGER_UPDATE = "UpdateMe"
TRIGGER_UPDATE_LOWER = TRIGGER_UPDATE.lower()
TRIGGER_SUBSCRIBE = "SubscribeMe"
TRIGGER_SUBSCRIBE_LOWER = TRIGGER_SUBSCRIBE.lower()
TRIGGER_SUBSCRIBE_ALL = "SubscribeAll"
TRIGGER_SUBSCRIBE_ALL_LOWER = TRIGGER_SUBSCRIBE_ALL.lower()
TRIGGER_COMBINED = "|".join([TRIGGER_UPDATE_LOWER, TRIGGER_SUBSCRIBE_LOWER, TRIGGER_SUBSCRIBE_ALL_LOWER])

TRACKING_INFO_URL = "https://www.reddit.com/r/UpdateMeBot/comments/g86jrs/subreddit_tracking_info/"
INFO_POST = "https://www.reddit.com/r/UpdateMeBot/comments/4wirnm/updatemebot_info/"
NEW_POST = "https://www.reddit.com/r/UpdateMeBot/comments/4wirnm/updatemebot_info/"

DB_TO_MIGRATE_FROM = r"C:\Users\greg\Desktop\PyCharm\UpdateMeBot\databaseOld.db"
