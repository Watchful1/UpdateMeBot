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
# haven't installed the new app (see migration.py). Worded like the bulk user
# message the admins approved: nothing that points the reader at moderators.
# {subreddit} is the post's subreddit, {author} a profile's owner, {link} the
# announcement post.
MIGRATION_STATUS_URL = "https://reddit.watchful.gr/api/v1/updateme/migration-status"
MIGRATION_POST = "https://www.reddit.com/r/UpdateMeBot/comments/1xlo20m/updatemebot_is_moving_to_devvit_part_2/"
MIGRATION_NOTICE = \
	"**Your notifications for r/{subreddit} will stop soon.** UpdateMeBot is moving to Reddit's developer " \
	"platform. Unlike the current bot, apps on the platform only work in subreddits where the app is " \
	"installed. [Learn more]({link})"
# Profiles can't install the app at all.
MIGRATION_NOTICE_PROFILE = \
	"**Your notifications for u/{author}'s profile posts will stop soon.** UpdateMeBot is moving to Reddit's " \
	"developer platform, and apps on the platform can't be installed on user profiles. [Details]({link})"

# The one-off bulk message (scripts/migration_campaign.py, rendered by
# migration_message.py) to people notified recently from subreddits that haven't
# installed. Final wording approved by the admins 2026-11-01. It says nothing
# that suggests the reader should do anything, since that ends in people
# messaging moderators. {places} is "r/A" or "r/A, r/B and r/C"; {there} is
# that same list or "these subreddits".
MIGRATION_MESSAGE_SUBJECT_ONE = "Your UpdateMeBot notifications for {place} will stop soon"
MIGRATION_MESSAGE_SUBJECT_MANY = "Your UpdateMeBot notifications for {place} and {others} will stop soon"
MIGRATION_MESSAGE_BODY = \
	"Hi! You use UpdateMeBot to get notified about new posts in **{places}**.\n\n" \
	"UpdateMeBot is moving to Reddit's developer platform soon. Unlike the current bot, apps on the platform " \
	"only work in subreddits where the app is installed. When the switch happens, your notifications for " \
	"posts in {there} will stop.\n\n" \
	"Learn more about these changes, or ask questions on [the announcement post]({link}). " \
	"Replies sent to this message aren't read by a person."

# The modmail to moderators of affected subreddits (scripts/migration_modmail.py),
# sent from u/Watchful1 so replies reach a person. The usage clause is left out
# below MODMAIL_MIN_NOTIFICATIONS, where the number would read as a reason not
# to bother.
MODMAIL_MIN_NOTIFICATIONS = 20
MODMAIL_SUBJECT = "About UpdateMeBot in r/{subreddit}"
MODMAIL_USAGE = ", and in the last 90 days the bot sent {notifications} notifications for posts in your sub"
MODMAIL_BODY = \
	"Hi r/{subreddit} mods,\n\n" \
	"I'm u/Watchful1, and I run UpdateMeBot.\n\n" \
	"UpdateMeBot lets readers follow an author. When someone enjoys a post, especially a story with more parts " \
	"to come, they can comment \"UpdateMe!\" or message the bot. It then sends them a private message whenever " \
	"that author posts in the same subreddit again.\n\n" \
	"{subscribers} people are subscribed to authors in r/{subreddit}{usage}.\n\n" \
	"Like other bots, UpdateMeBot is moving to Reddit's Developer Platform soon. Apps on the platform only run " \
	"in subreddits whose moderators have installed them, so once the switch happens, {those} notifications will " \
	"stop unless r/{subreddit} installs the new version. Installing takes about a minute, and the instructions " \
	"are [here]({link}). The bot works the same as it does today, and you can uninstall it any time.\n\n" \
	"If you'd rather not have it in r/{subreddit}, just reply to this message and I'll make a note not to " \
	"contact you about it again.\n\n" \
	"Thanks,  \nu/Watchful1"
