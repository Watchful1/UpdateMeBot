import praw
import OAuth2Util
import sqlite3
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

conn = sqlite3.connect('database.db')
c = conn.cursor()
c.execute('''CREATE TABLE stocks
             (date text, trans text, symbol text, qty real, price real)''')

# Insert a row of data
c.execute("INSERT INTO stocks VALUES ('2006-01-05','BUY','RHAT',100,35.14)")

# Save (commit) the changes
conn.commit()

# We can also close the connection if we are done with it.
# Just be sure any changes have been committed or they will be lost.`
conn.close()



# filters
# user: username of submitter, accepts any string
# type: comment or thread, do not include for both
# subreddit: subreddit the item was submitted to. Accepts multiple
