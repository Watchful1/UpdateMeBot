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
			Subscriber varchar(80) NOT NULL,
			SubscribedTo varchar(80) NOT NULL,
			Subreddit varchar(80),
			LastChecked timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
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


def addSubsciption(Subscriber, SubscribedTo, Subreddit):
	c = dbConn.cursor()
	c.execute('''
		INSERT INTO subscriptions
		(Subscriber, SubscribedTo, Subreddit)
		VALUES (?, ?, ?)
	''', (Subscriber, SubscribedTo, Subreddit))


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


def deleteSubscription(Subscriber, SubscribedTo, Subreddit):
	c = dbConn.cursor()
	c.execute('''
    		DELETE FROM subscriptions
    		WHERE Subscriber = ?
    		    AND SubscribedTo = ?
    		    AND Subreddit = ?
    ''', (Subscriber, SubscribedTo, Subreddit))


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
