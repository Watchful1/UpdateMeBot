import sqlite3
from datetime import datetime

dbConn = 0


def init():
	global dbConn

	dbConn = sqlite3.connect('database.db')

	setup()


def close():
	dbConn.commit()
	dbConn.close()


def setup():
	c = dbConn.cursor()
	c.execute('''
		CREATE TABLE IF NOT EXISTS subscriptions (
			ID INTEGER PRIMARY KEY AUTOINCREMENT,
			Subscriber VARCHAR(80) NOT NULL,
			SubscribedTo VARCHAR(80),
			Subreddit VARCHAR(80) NOT NULL,
			LastChecked TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
			Single BOOLEAN DEFAULT 1,
			Approved BOOLEAN DEFAULT 1,
			UNIQUE (Subscriber, SubscribedTo, Subreddit)
		)
	''')
	c.execute('''
		CREATE TABLE IF NOT EXISTS subredditWhitelist (
			ID INTEGER PRIMARY KEY AUTOINCREMENT,
			Subreddit VARCHAR(80) NOT NULL,
			Status INTEGER DEFAULT 0,
			DefaultSubscribe BOOLEAN DEFAULT 0,
			NextNotice INTEGER DEFAULT 5,
			UNIQUE (Subreddit)
		)
	''')
	c.execute('''
		CREATE TABLE IF NOT EXISTS threads (
			ID INTEGER PRIMARY KEY AUTOINCREMENT,
			ThreadID VARCHAR(80) NOT NULL,
			CommentID VARCHAR(80) NOT NULL,
			SubscribedTo VARCHAR(80),
			Subreddit VARCHAR(80) NOT NULL,
			ParentAuthor VARCHAR(80) NOT NULL,
			CommentCreated TIMESTAMP NOT NULL,
			CurrentCount INTEGER DEFAULT 0,
			Single BOOLEAN,
			UNIQUE (ThreadID)
		)
	''')
	c.execute('''
		CREATE TABLE IF NOT EXISTS commentSearch (
			ID INTEGER PRIMARY KEY AUTOINCREMENT,
			Type VARCHAR(80) NOT NULL,
			Timestamp TIMESTAMP NOT NULL,
			UNIQUE (Type)
		)
	''')
	dbConn.commit()


def printSubscriptions():
	c = dbConn.cursor()
	for row in c.execute('''
		SELECT *
		FROM subscriptions
		WHERE Approved = 1
	'''):
		print(row)


def getSubscriptions():
	c = dbConn.cursor()
	return c.execute('''
		SELECT ID, Subscriber, SubscribedTo, Subreddit, LastChecked
		FROM subscriptions
		WHERE Approved = 1
		GROUP BY Subreddit, SubscribedTo, Subscriber
		ORDER BY Subreddit, LastChecked
	''')


def getMySubscriptions(Subscriber):
	c = dbConn.cursor()
	output = c.execute('''
		SELECT SubscribedTo, Subreddit, Single
		FROM subscriptions
		WHERE Subscriber = ?
			AND Approved = 1
		ORDER BY Subreddit, Single, SubscribedTo
	''', (Subscriber,))

	results = []

	for row in output:
		results.append({'subscribedTo': row[0], 'subreddit': row[1], 'single': row[2] == 1})

	return results


def addSubscription(Subscriber, SubscribedTo, Subreddit, date=datetime.now(), single=True):
	c = dbConn.cursor()
	try:
		c.execute('''
			INSERT INTO subscriptions
			(Subscriber, SubscribedTo, Subreddit, LastChecked, Single)
			VALUES (?, ?, ?, ?, ?)
		''', (Subscriber, SubscribedTo, Subreddit, date.strftime("%Y-%m-%d %H:%M:%S"), single))
	except sqlite3.IntegrityError:
		return False

	return True


def getSubscriptionType(Subscriber, SubscribedTo, Subreddit):
	c = dbConn.cursor()
	result = c.execute('''
		SELECT Single FROM subscriptions
		WHERE Subscriber = ?
			AND SubscribedTo = ?
			AND Subreddit = ?
			AND Approved = 1
	''', (Subscriber, SubscribedTo, Subreddit))

	if result.fetchone()[0] == 1:
		return True
	else:
		return False


def setSubscriptionType(Subscriber, SubscribedTo, Subreddit, single):
	c = dbConn.cursor()
	c.execute('''
		UPDATE subscriptions
		SET Single = ?
		WHERE Subscriber = ?
			AND SubscribedTo = ?
			AND Subreddit = ?
			AND Approved = 1
	''', (single, Subscriber, SubscribedTo, Subreddit))


def checkSubscription(ID, date = datetime.now()):
	c = dbConn.cursor()
	c.execute('''
		UPDATE subscriptions
		SET LastChecked = ?
		WHERE ID = ?
			AND Approved = 1
	''', (date.strftime("%Y-%m-%d %H:%M:%S"), ID))


def checkSubreddit(Subreddit, date = datetime.now()):
	c = dbConn.cursor()
	c.execute('''
		UPDATE subscriptions
		SET LastChecked = ?
		WHERE Subreddit = ?
			AND Approved = 1
	''', (date.strftime("%Y-%m-%d %H:%M:%S"), Subreddit))


def removeSubscription(Subscriber, SubscribedTo, Subreddit):
	c = dbConn.cursor()
	c.execute('''
    	DELETE FROM subscriptions
    	WHERE Subscriber = ?
    	    AND SubscribedTo = ?
    	    AND Subreddit = ?
			AND Approved = 1
    ''', (Subscriber, SubscribedTo, Subreddit))

	if c.rowcount == 1:
		return True
	else:
		return False


def checkRemoveSubscription(Subscriber, SubscribedTo, Subreddit):
	if getSubscriptionType(Subscriber, SubscribedTo, Subreddit):
		return True
	else:
		removeSubscription(Subscriber, SubscribedTo, Subreddit)
		return False


def removeAllSubscriptions(Subscriber):
	c = dbConn.cursor()
	c.execute('''
    	DELETE FROM subscriptions
    	WHERE Subscriber = ?
    ''', (Subscriber,))


def clearSubscriptions():
	c = dbConn.cursor()
	c.execute('''
		DELETE FROM subscriptions
    ''')


def resetAllSubscriptionTimes():
	c = dbConn.cursor()
	c.execute('''
		UPDATE subscriptions
		SET LastChecked = '2016-07-18 17:00:00'
    ''')


def isSubredditWhitelisted(Subreddit):
	c = dbConn.cursor()
	result = c.execute('''
		SELECT * FROM subredditWhitelist
		WHERE Subreddit = ?
			and Status <> 0
	''', (Subreddit,))

	if result.fetchone():
		return True
	else:
		return False


def addDeniedRequest(Subscriber, SubscribedTo, Subreddit, date = datetime.now(), single = True):
	c = dbConn.cursor()
	try:
		c.execute('''
			INSERT INTO subscriptions
			(Subscriber, SubscribedTo, Subreddit, LastChecked, Single, Approved)
			VALUES (?, ?, ?, ?, ?, 0)
		''', (Subscriber, SubscribedTo, Subreddit, date.strftime("%Y-%m-%d %H:%M:%S"), single))
	except sqlite3.IntegrityError:
		return False

	return True


def getDeniedSubscriptions(Subreddit):
	c = dbConn.cursor()
	output = c.execute('''
		SELECT Subscriber, SubscribedTo, Single
		FROM subscriptions
		WHERE Subreddit = ?
			AND Approved = 0
	''', (Subreddit,))

	results = {}

	for row in output:
		if row[0] not in results:
			results[row[0]] = []
		results[row[0]].append({'subscribedTo': row[1], 'single': True if row[2] == 1 else False})

	return results


def activateSubreddit(Subreddit):
	c = dbConn.cursor()
	result = c.execute('''
		SELECT count(*)
		FROM subredditWhitelist
		WHERE Subreddit = ?
	''', (Subreddit,))

	if result.fetchone()[0] == 0:
		c.execute('''
			INSERT INTO subredditWhitelist
			(Subreddit, Status)
			VALUES (?, 1)
		''', (Subreddit,))
	else:
		c.execute('''
			UPDATE subredditWhitelist
			SET Status = 1
			WHERE subreddit = ?
		''', (Subreddit,))

	c.execute('''
		UPDATE subscriptions
		SET Approved = 1
		WHERE subreddit = ?
	''', (Subreddit,))


def subredditDefaultSubscribe(Subreddit):
	c = dbConn.cursor()
	result = c.execute('''
		SELECT DefaultSubscribe
		FROM subredditWhitelist
		WHERE Subreddit = ?
	''', (Subreddit,))

	if result.fetchone()[0] == 1:
		return True
	else:
		return False


def getDeniedRequestsCount(Subreddit):
	c = dbConn.cursor()
	result = c.execute('''
		SELECT count(*)
		FROM subscriptions
		WHERE Approved = 0
			AND Subreddit = ?
	''', (Subreddit,))

	return result.fetchone()[0]


def checkUpdateDeniedRequestsNotice(Subreddit, current):
	c = dbConn.cursor()
	c.execute('''
		SELECT NextNotice
		FROM subredditWhitelist
		WHERE Subreddit = ?
	''', (Subreddit,))

	results = c.fetchall()

	if len(results) == 0:
		c.execute('''
			INSERT INTO subredditWhitelist
			(Subreddit, Status)
			VALUES (?, 0)
		''', (Subreddit,))
		notice = 5
	else:
		notice = results[0][0]

	if current >= notice:
		c.execute('''
			UPDATE subredditWhitelist
			SET NextNotice = ?
			WHERE Subreddit = ?
		''', (current*2, Subreddit))
		return True
	else:
		return False


def addThread(threadID, commentID, subscribedTo, subreddit, parentAuthor, commentCreated, currentCount, single):
	c = dbConn.cursor()
	try:
		c.execute('''
			INSERT INTO threads
			(ThreadID, CommentID, SubscribedTo, Subreddit, ParentAuthor, CommentCreated, CurrentCount, Single)
			VALUES (?, ?, ?, ?, ?, ?, ?, ?)
		''', (threadID, commentID, subscribedTo, subreddit, parentAuthor, commentCreated.strftime("%Y-%m-%d %H:%M:%S"),
		      currentCount, single))
	except sqlite3.IntegrityError:
		return False

	return True


def isThreadReplied(threadID):
	c = dbConn.cursor()
	result = c.execute('''
		SELECT * FROM threads
		WHERE ThreadID = ?
	''', (threadID,))

	if result.fetchone():
		return True
	else:
		return False


def getAuthorSubscribersCount(author, Subreddit):
	c = dbConn.cursor()
	result = c.execute('''
		SELECT count(*)
		FROM subscriptions
		WHERE Approved = 0
			AND Subreddit = ?
			AND SubscribedTo = ?
	''', (Subreddit, author))

	return result.fetchone()[0]


def getCommentSearchTime(searchType):
	c = dbConn.cursor()
	result = c.execute('''
		SELECT Timestamp
		FROM commentSearch
		WHERE Type = ?
	''', (searchType,))

	stringTime = result.fetchone()

	if not stringTime:
		return None
	else:
		return datetime.strptime(stringTime[0], "%Y-%m-%d %H:%M:%S")


def updateCommentSearchSeconds(searchType, date):
	c = dbConn.cursor()
	c.execute('''
			INSERT OR REPLACE INTO commentSearch
			(Type, Timestamp)
			VALUES (?, ?)
		''', (searchType, date.strftime("%Y-%m-%d %H:%M:%S")))


def getIncorrectThreads(cutoffDate):
	c = dbConn.cursor()
	c.execute('''
		SELECT threads.ThreadID
			,threads.CommentID
			,threads.SubscribedTo
			,threads.Subreddit
			,threads.Single
			,subscriptionCount.Count
		FROM threads
		LEFT JOIN
			(
				SELECT SubscribedTo
					,Subreddit
					,count(*) as Count
				FROM subscriptions
				GROUP BY SubscribedTo, Subreddit
			) AS subscriptionCount
				ON threads.SubscribedTo = subscriptionCount.SubscribedTo
					AND threads.Subreddit = subscriptionCount.Subreddit
		WHERE threads.CurrentCount <> subscriptionCount.Count
			AND threads.CommentCreated > ?
	''', (cutoffDate.strftime("%Y-%m-%d %H:%M:%S"),))

	output = []
	for thread in c.fetchall():
		output.append({'threadID': thread[0], 'commentID': thread[1], 'subscribedTo': thread[2],
		               'subreddit': thread[3], 'single': True if thread[4] == 1 else False, 'currentCount': thread[5]})

	return output


def updateCurrentThreadCount(threadID, count):
	c = dbConn.cursor()
	c.execute('''
		UPDATE threads
		SET CurrentCount = ?
		WHERE ThreadID = ?
	''', (count, threadID))
