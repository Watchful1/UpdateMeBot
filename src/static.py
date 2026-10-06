import re

USER_AGENT = "UpdateMeBot (by /u/Watchful1)"
OWNER = "Watchful1"
ACCOUNT_NAME = "Watchful1BotTest"
DATABASE_NAME = "database.db"
BACKUP_FOLDER_NAME = "backup"
BLACKLISTED_ACCOUNTS = ['[deleted]', 'AutoModerator', 'NoSleepAutoBot', 'HFYWaffle']

TRIGGER_UPDATE = "UpdateMe"
TRIGGER_UPDATE_LOWER = TRIGGER_UPDATE.lower()
TRIGGER_SUBSCRIBE = "SubscribeMe"
TRIGGER_SUBSCRIBE_LOWER = TRIGGER_SUBSCRIBE.lower()
TRIGGER_SUBSCRIBE_ALL = "SubscribeAll"
TRIGGER_SUBSCRIBE_ALL_LOWER = TRIGGER_SUBSCRIBE_ALL.lower()
TRIGGER_COMBINED = "|".join([TRIGGER_UPDATE_LOWER, TRIGGER_SUBSCRIBE_LOWER, TRIGGER_SUBSCRIBE_ALL_LOWER])

REGEX_TRIGGER_SUBSCRIBE = re.compile(r"\bsubscribeme\b", re.IGNORECASE)
REGEX_TRIGGER_UPDATE = re.compile(r"\b(please)?(updateme)(bot)?\b", re.IGNORECASE)

TRACKING_INFO_URL = "https://www.reddit.com/r/UpdateMeBot/comments/g86jrs/subreddit_tracking_info/"
INFO_POST = "https://www.reddit.com/r/UpdateMeBot/comments/ggotgx/updatemebot_info_v20/"
NEW_POST = "https://www.reddit.com/r/UpdateMeBot/comments/juh0f8/new_features_title_in_message_subject_and_recent/"
ABBREV_POST = "https://www.reddit.com/r/UpdateMeBot/comments/jyj02k/abbreviated_notifications_setting/"

STAT_MINIMUM = 10

# The Devvit migration notice, appended to notifications from subreddits that
# haven't installed the new app (see migration.py). Wording pending admin
# approval; {subreddit} is the post's subreddit name, {link} the announcement.
MIGRATION_STATUS_URL = "https://reddit.watchful.gr/api/v1/updateme/migration-status"
MIGRATION_POST = "https://www.reddit.com/r/UpdateMeBot/comments/1w0fnmb/uupdatemebot_is_moving_to_a_devvit_app/"
MIGRATION_NOTICE = \
	"**UpdateMeBot is moving to Reddit's developer platform soon, and r/{subreddit} hasn't installed it yet. " \
	"If that doesn't change, notifications for posts in r/{subreddit} will stop.**"
MIGRATION_INSTALL_ASK = "If you're a moderator of r/{subreddit}, the details explain how to install it."
