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
# approval. {subreddit} is the post's subreddit, {author} a profile's owner,
# {link} the announcement post.
MIGRATION_STATUS_URL = "https://reddit.watchful.gr/api/v1/updateme/migration-status"
MIGRATION_POST = "https://www.reddit.com/r/UpdateMeBot/comments/1w0fnmb/uupdatemebot_is_moving_to_a_devvit_app/"
MIGRATION_NOTICE = \
	"**Your notifications for r/{subreddit} will stop soon.** UpdateMeBot is moving to Reddit's developer " \
	"platform. Unlike the current bot, apps on the platform only work in subreddits whose moderators have " \
	"installed them, and r/{subreddit} hasn't yet. Moderators can install it from [here]({link})."
# Moderators who opted out asked not to be pointed at again: no install ask,
# and "hasn't" rather than "hasn't yet".
MIGRATION_NOTICE_OPTED_OUT = \
	"**Your notifications for r/{subreddit} will stop soon.** UpdateMeBot is moving to Reddit's developer " \
	"platform. Unlike the current bot, apps on the platform only work in subreddits whose moderators have " \
	"installed them, and r/{subreddit} hasn't. [Details]({link})"
# Profiles can't install the app at all.
MIGRATION_NOTICE_PROFILE = \
	"**Your notifications for u/{author}'s profile posts will stop soon.** UpdateMeBot is moving to Reddit's " \
	"developer platform, and apps on the platform can't be installed on user profiles. [Details]({link})"
