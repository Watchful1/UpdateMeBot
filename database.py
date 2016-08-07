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
			SubscribedTo VARCHAR(80) NOT NULL,
			Subreddit VARCHAR(80),
			LastChecked TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
			Single BOOLEAN DEFAULT 1,
			UNIQUE (Subscriber, SubscribedTo, Subreddit)
		)
	''')
	dbConn.commit()


def printSubscriptions():
	c = dbConn.cursor()
	for row in c.execute('''
		SELECT *
		FROM subscriptions
	'''):
		print(row)


def getSubscriptions():
	c = dbConn.cursor()
	return c.execute('''
		SELECT ID, Subscriber, SubscribedTo, Subreddit, LastChecked
		FROM subscriptions
		GROUP BY Subreddit, SubscribedTo, Subscriber
		ORDER BY Subreddit, LastChecked
	''')


def getMySubscriptions(Subscriber):
	c = dbConn.cursor()
	output = c.execute('''
		SELECT SubscribedTo, Subreddit, Single
		FROM subscriptions
		WHERE Subscriber = ?
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
			and SubscribedTo = ?
			and Subreddit = ?
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
			and SubscribedTo = ?
			and Subreddit = ?
	''', (single, Subscriber, SubscribedTo, Subreddit))


def checkSubscription(ID, date = datetime.now()):
	c = dbConn.cursor()
	c.execute('''
		UPDATE subscriptions
		SET LastChecked = ?
		WHERE ID = ?
	''', (date.strftime("%Y-%m-%d %H:%M:%S"), ID))


def checkSubreddit(Subreddit, date = datetime.now()):
	c = dbConn.cursor()
	c.execute('''
		UPDATE subscriptions
		SET LastChecked = ?
		WHERE Subreddit = ?
	''', (date.strftime("%Y-%m-%d %H:%M:%S"), Subreddit))


def removeSubscription(Subscriber, SubscribedTo, Subreddit):
	c = dbConn.cursor()
	result = c.execute('''
    		DELETE FROM subscriptions
    		WHERE Subscriber = ?
    		    AND SubscribedTo = ?
    		    AND Subreddit = ?
    ''', (Subscriber, SubscribedTo, Subreddit))

	if c.rowcount == 1:
		return True
	else:
		return False


def removeAllSubscriptions(Subscriber):
	c = dbConn.cursor()
	result = c.execute('''
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
