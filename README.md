# UpdateMeBot

This is the code for [u/UpdateMeBot](https://www.reddit.com/user/UpdateMeBot), which messages you when an author you follow posts again. It was built mainly for serial fiction subreddits, where people want the next chapter as soon as it's up ([info post](https://www.reddit.com/r/UpdateMeBot/comments/ggotgx/updatemebot_info_v20/)). It's been running since 2016 and has about 2.4 million subscriptions. I'm currently porting it to Reddit's [Devvit](https://developers.reddit.com/) platform in TypeScript.

## How it works

Most of the work is checking every enabled subreddit for new posts without spending too many API calls. The bot profiles how many posts an hour each subreddit gets, then packs quiet subreddits together into combined `a+b+c` listings of about 50 posts an hour each. A group gets split up if it errors or returns more than 500 new posts, and any subreddit that hasn't been checked in over an hour is scanned on its own. It also rechecks recent posts to catch deletions.

Notifications go into a queue that's sent in batches sized to the Reddit rate limit, so a big author posting just spreads over a few loops.

Comments with trigger words come from a separate ingest process (not in this repo), passed in as a SQLite file with `--ingest_db`.

## Tech

Python, SQLAlchemy on SQLite, and PRAW through [PrawWrapper](https://github.com/Watchful1/PrawWrapper), which also gives the pytest suite a fake Reddit to run against. Errors get posted to Discord with [DiscordLogging](https://github.com/Watchful1/DiscordLogging), and it exports Prometheus metrics.
