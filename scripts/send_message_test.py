import logging.handlers
import sys
import signal
import time
import traceback
import discord_logging
import praw_wrapper
import argparse

log = discord_logging.init_logging()

if __name__ == "__main__":
	reddit = praw_wrapper.Reddit("UpdateMeBot", user_agent="UpdateMeBot (by /u/Watchful1)")

	target_user = "FinalArtichoke"
	subject = "UpdateMeBot Here! Post by u/mybrotherareyou in r/u_mybrotherareyou: Daughter's insights"
	body = """UpdateMeBot here!

u/mybrotherareyou has posted a new thread in r/u_mybrotherareyou

[**Daughter's insights**](https://www.reddit.com/r/u_mybrotherareyou/comments/1lvy9dd/daughters_insights/)

*****

Recent posts:[*](https://www.reddit.com/r/UpdateMeBot/comments/jyj02k/abbreviated_notifications_setting/)
[My son is very shy and sensitive...](https://www.reddit.com/r/u_mybrotherareyou/comments/1lvhf8y/my_son_is_very_shy_and_sensitive/)
[Brought a new pack of condoms to work today](https://www.reddit.com/r/u_mybrotherareyou/comments/1ltsskx/brought_a_new_pack_of_condoms_to_work_today/)
[Relatable after spending the afternoon outdoors](https://www.reddit.com/r/u_mybrotherareyou/comments/1lsglja/relatable_after_spending_the_afternoon_outdoors/)

*****

[Click here](https://www.reddit.com/message/compose/?to=UpdateMeBot&subject=Remove&message=Remove%20u%2Fmybrotherareyou%20r%2Fu_mybrotherareyou) to remove your subscription.

*****

|[^(Info)](https://www.reddit.com/r/UpdateMeBot/comments/ggotgx/updatemebot_info_v20/)|[^(Request Update)](https://www.reddit.com/message/compose/?to=UpdateMeBot&subject=Update&message=SubscribeMe%21%20u%2Fusername%20r%2Fsubreddit)|[^(Your Updates)](https://www.reddit.com/message/compose/?to=UpdateMeBot&subject=List%20Of%20Updates&message=MyUpdates)|[^(Feedback)](https://www.reddit.com/message/compose/?to=Watchful1&subject=UpdateMeBot%20Feedback)|
|-|-|-|-|"""

	result = reddit.send_message(target_user, subject, body)
