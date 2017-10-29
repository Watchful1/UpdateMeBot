import sqlite3
from datetime import datetime
import globals

dbConn = 0
log = 0


def init(logIn):
	global dbConn
	dbConn = sqlite3.connect(globals.DATABASE_NAME)

	global log
	log = logIn

	setup()


def close():
	dbConn.commit()
	dbConn.close()


migrations = {
	1: [
		'''
			ALTER TABLE subscriptions
			ADD Filter VARCHAR(1000)
		''',
		'''
			ALTER TABLE subredditWhitelist
			ADD Filter VARCHAR(1000)
		'''
	]
}


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
			AlwaysPM BOOLEAN DEFAULT 0,
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
	c.execute('''
		CREATE TABLE IF NOT EXISTS blacklist (
			ID INTEGER PRIMARY KEY AUTOINCREMENT,
			Name VARCHAR(80) NOT NULL,
			IsSubreddit BOOLEAN DEFAULT 0,
			UNIQUE (Name, IsSubreddit)
		)
	''')
	c.execute('''
		CREATE TABLE IF NOT EXISTS prompts (
			ID INTEGER PRIMARY KEY AUTOINCREMENT,
			User VARCHAR(80) NOT NULL,
			Subreddit VARCHAR(80) NOT NULL,
			UNIQUE (User, Subreddit)
		)
	''')
	dbConn.commit()

	results = c.execute('''
		PRAGMA USER_VERSION
	''')
	result = results.fetchone()[0]

	log.debug("Found database version: "+str(result))
	if len(migrations) > result:
		log.debug("Found migrations: "+str(len(migrations) - result))

		for i in range(result + 1, len(migrations) + 1):
			log.debug("Applying version: "+str(i))

			for migration in migrations[i]:
				c.execute(migration)

			c.execute('''
				PRAGMA USER_VERSION = {}
			'''.format(i))





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


def getSubscribedSubreddits():
	c = dbConn.cursor()
	results = []
	for row in c.execute('''
		SELECT Subreddit, MIN(LastChecked)
		FROM subscriptions
		WHERE Approved = 1
		GROUP BY subreddit
	'''):
		results.append({'subreddit': row[0], 'lastChecked': row[1]})

	return results


def getSubredditAuthorSubscriptions(Subreddit, SubscribedTo):
	c = dbConn.cursor()
	results = []
	for row in c.execute('''
		SELECT ID, Subscriber, LastChecked, Single
		FROM subscriptions
		WHERE Subreddit = ?
			and SubscribedTo = ?
			and Approved = 1
	''', (Subreddit, SubscribedTo)):
		results.append({'ID': row[0], 'subscriber': row[1], 'lastChecked': row[2], 'single': row[3] == 1})

	return results


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

	dbConn.commit()
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

	if result is not None and result.fetchone()[0] == 1:
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
	dbConn.commit()


def checkSubscription(ID, date=datetime.now()):
	c = dbConn.cursor()
	c.execute('''
		UPDATE subscriptions
		SET LastChecked = ?
		WHERE ID = ?
			AND Approved = 1
	''', (date.strftime("%Y-%m-%d %H:%M:%S"), ID))
	dbConn.commit()


def checkSubreddit(Subreddit, date=datetime.now()):
	c = dbConn.cursor()
	c.execute('''
		UPDATE subscriptions
		SET LastChecked = ?
		WHERE Subreddit = ?
			AND Approved = 1
	''', (date.strftime("%Y-%m-%d %H:%M:%S"), Subreddit))
	dbConn.commit()


def removeSubscription(Subscriber, SubscribedTo, Subreddit):
	c = dbConn.cursor()
	c.execute('''
    	DELETE FROM subscriptions
    	WHERE Subscriber = ?
    	    AND SubscribedTo = ?
    	    AND Subreddit = ?
			AND Approved = 1
    ''', (Subscriber, SubscribedTo, Subreddit))
	dbConn.commit()

	if c.rowcount == 1:
		return True
	else:
		return False


def checkRemoveSubscription(ID, single, date):
	c = dbConn.cursor()
	if single:
		c.execute('''
	        DELETE FROM subscriptions
	        WHERE ID = ?
	    ''', (ID,))
	else:
		c.execute('''
			UPDATE subscriptions
			SET LastChecked = ?
			WHERE ID = ?
		''', (date.strftime("%Y-%m-%d %H:%M:%S"), ID))
	dbConn.commit()


def removeAllSubscriptions(Subscriber):
	c = dbConn.cursor()
	c.execute('''
    	DELETE FROM subscriptions
    	WHERE Subscriber = ?
    ''', (Subscriber,))
	dbConn.commit()


def clearSubscriptions():
	c = dbConn.cursor()
	c.execute('''
		DELETE FROM subscriptions
    ''')
	dbConn.commit()


def resetAllSubscriptionTimes():
	c = dbConn.cursor()
	c.execute('''
		UPDATE subscriptions
		SET LastChecked = '2016-07-18 17:00:00'
    ''')
	dbConn.commit()


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


def addDeniedRequest(Subscriber, SubscribedTo, Subreddit, date=datetime.now(), single=True):
	c = dbConn.cursor()
	try:
		c.execute('''
			INSERT INTO subscriptions
			(Subscriber, SubscribedTo, Subreddit, LastChecked, Single, Approved)
			VALUES (?, ?, ?, ?, ?, 0)
		''', (Subscriber, SubscribedTo, Subreddit, date.strftime("%Y-%m-%d %H:%M:%S"), single))
	except sqlite3.IntegrityError:
		return False

	dbConn.commit()
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


def activateSubreddit(Subreddit, DefaultSubscribe):
	c = dbConn.cursor()
	result = c.execute('''
		SELECT count(*)
		FROM subredditWhitelist
		WHERE Subreddit = ?
	''', (Subreddit,))

	if result.fetchone()[0] == 0:
		c.execute('''
			INSERT INTO subredditWhitelist
			(Subreddit, Status, DefaultSubscribe)
			VALUES (?, 1, ?)
		''', (Subreddit,DefaultSubscribe))
	else:
		c.execute('''
			UPDATE subredditWhitelist
			SET Status = 1
				,DefaultSubscribe = ?
			WHERE subreddit = ?
		''', (DefaultSubscribe, Subreddit))

	c.execute('''
		UPDATE subscriptions
		SET Approved = 1
		WHERE subreddit = ?
	''', (Subreddit,))
	dbConn.commit()


def subredditDefaultSubscribe(subreddit):
	c = dbConn.cursor()
	results = c.execute('''
		SELECT DefaultSubscribe
		FROM subredditWhitelist
		WHERE Subreddit = ?
	''', (subreddit,))

	result = results.fetchone()

	if result == 1:
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
		dbConn.commit()
		return True
	else:
		dbConn.commit()
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

	dbConn.commit()
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
	dbConn.commit()


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
	dbConn.commit()


def deleteComment(threadID, author):
	c = dbConn.cursor()
	result = c.execute('''
		SELECT CommentID
			,ParentAuthor
		FROM threads
		WHERE ThreadID = ?
	''', (threadID,))

	result = result.fetchone()

	if not result: return None
	if result[1] != author: return None

	c.execute('''
        DELETE FROM threads
	    WHERE ThreadID = ?
	''', (threadID,))

	dbConn.commit()
	return result[0]


def alwaysPMForSubreddit(subreddit):
	c = dbConn.cursor()
	results = c.execute('''
		SELECT AlwaysPM
		FROM subredditWhitelist
		WHERE Subreddit = ?
	''', (subreddit,))

	result = results.fetchone()

	if not result: return None  # shouldn't happen
	if result == 1:
		return True
	else:
		return False


def setAlwaysPMForSubreddit(subreddit, alwaysPM):
	c = dbConn.cursor()
	c.execute('''
		UPDATE subredditWhitelist
		SET AlwaysPM = ?
		WHERE Subreddit = ?
	''', (alwaysPM, subreddit))
	dbConn.commit()


def blacklist(name, isSubreddit, add):
	c = dbConn.cursor()
	if add:
		try:
			c.execute('''
				INSERT INTO blacklist
				(Name, IsSubreddit)
				VALUES (?, ?)
			''', (name, isSubreddit))
			dbConn.commit()
		except sqlite3.IntegrityError:
			return False

		return True
	else:
		c.execute('''
			DELETE FROM blacklist
			WHERE Name = ?
				and IsSubreddit = ?
		''', (name, isSubreddit))
		dbConn.commit()

		if c.rowcount == 1:
			return True
		else:
			return False


def isBlacklisted(name=None, subreddit=None):
	c = dbConn.cursor()
	output = False
	if name:
		result = c.execute('''
			SELECT * FROM blacklist
			WHERE Name = ?
				and IsSubreddit = 0
		''', (name,))

		if result.fetchone():
			output = True

	if subreddit:
		result = c.execute('''
			SELECT * FROM blacklist
			WHERE Name = ?
				and IsSubreddit = 1
		''', (subreddit,))

		if result.fetchone():
			output = True

	return output


def addPrompt(user, subreddit):
	c = dbConn.cursor()
	c.execute('''
		INSERT INTO prompts
		(User, Subreddit)
		VALUES (?, ?)
	''', (user, subreddit))
	dbConn.commit()


def removePrompt(user, subreddit):
	c = dbConn.cursor()
	c.execute('''
		DELETE FROM prompts
		WHERE User = ?
			and Subreddit = ?
	''', (user, subreddit))
	dbConn.commit()


def isPrompt(user, subreddit):
	c = dbConn.cursor()
	## using sub as a default couldn't possible go wrong
	results = c.execute('''
		SELECT COUNT(*)
		FROM prompts
		WHERE (User = ?
			OR User = 'sub')
			AND Subreddit = ?
	''', (user, subreddit))

	result = results.fetchone()

	if not result: return None  # shouldn't happen
	if result[0] >= 1:
		return True
	else:
		return False