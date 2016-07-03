import praw
import OAuth2Util
import time

r = praw.Reddit("bot:gr.watchful.subsbot (by /u/Watchful1)")
o = OAuth2Util.OAuth2Util(r)
o.refresh(force=True)

while True:
    print(r.get_me().comment_karma)
    time.sleep(30)