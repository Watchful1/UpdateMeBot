import sqlite3
import os.path

dbConn = 0


def init():
	global dbConn

	dbConn = sqlite3.connect('database.db')

	setup()


def setup():
	c = dbConn.cursor()
	c.execute('''
		CREATE TABLE IF NOT EXISTS subscriptions (
			ID int(11) NOT NULL AUTO_INCREMENT,
			Subscriber varchar(80) NOT NULL,
			SubscribedTo varchar(80) NOT NULL,
			Subreddit varchar(80) NOT NULL,
			LastChecked timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
			PRIMARY KEY (ID),
			UNIQUE KEY (Subscriber, SubscribedTo, Subreddit)
		)
	''')
