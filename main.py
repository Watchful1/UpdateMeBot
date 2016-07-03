import praw
import OAuth2Util
import time

r = praw.Reddit("subsbot:gr.watchful.subsbot (by /u/Watchful1)")
o = OAuth2Util.OAuth2Util(r)
o.refresh(force=True)

subs = {'Watchful1': {'user': 'thisisredditfacts'}}

for key, val in subs.items():
    if 'user' in val:
        user = r.get_redditor(val['user'])
        for comment in user.get_comments():
            print(str(comment.score)+': '+comment.body)

# filters
# user: username of submitter, accepts any string. Accepts multiple
# type: comment or thread, do not include for both
# subreddit: subreddit the item was submitted to. Accepts multiple
# karma: a minimum karma the item has to have
# age comments
