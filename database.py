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
			Unrestricted BOOLEAN DEFAULT 0,
			DefaultSubscribe BOOLEAN DEFAULT 0,
			UNIQUE (Subreddit)
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


def addSubsciption(Subscriber, SubscribedTo, Subreddit, date = datetime.now(), single = True):
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
	c.execute('''
		SELECT * FROM subredditWhitelist
		WHERE Subreddit = ?
	''', (Subreddit,))

	if c.rowcount >= 1:
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
	c.execute('''
		INSERT INTO subredditWhitelist
		(Subreddit)
		VALUES (?)
	''', (Subreddit,))
	c.execute('''
		UPDATE subscriptions
		SET Approved = 1
		WHERE subreddit = ?
	''', (Subreddit,))


def subredditDefaultSubscribe(Subreddit):
	c = dbConn.cursor()
	result = c.execute('''
		SELECT DefaultSubscribe FROM subredditWhitelist
		WHERE Subreddit = ?
	''', (Subreddit))

	if result.fetchone()[0] == 1:
		return True
	else:
		return False
