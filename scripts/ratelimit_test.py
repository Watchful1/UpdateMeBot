import praw
import time
import logging

handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
logger = logging.getLogger('prawcore')
logger.setLevel(logging.INFO)
logger.addHandler(handler)

r = praw.Reddit("Watchful1BotTest")

subs = ["askreddit", "askreddit", "askreddit", "askreddit"]

start_time = time.time()
last_time = start_time
for sub in subs:
	remaining = r._core._rate_limiter.remaining
	new_remaining = remaining
	if new_remaining is not None:
		new_remaining = remaining - 0.999
		#r._core._rate_limiter.remaining = new_remaining
	logger.info(f"{remaining} to {new_remaining}")
	for submission in r.subreddit(sub).new():
		continue
	logger.info(f"{round(time.time() - start_time, 2)} seconds / {round(time.time() - last_time, 2)} delta")
	last_time = time.time()
	logger.info(str(r.auth.limits) + " : " + str(int(r.auth.limits['reset_timestamp']) - time.time()))
