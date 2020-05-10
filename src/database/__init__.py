from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import discord_logging
import time
from datetime import timedelta
from shutil import copyfile

Base = declarative_base()

import static
import utils
from ._subscription import _DatabaseSubscriptions
from ._user import _DatabaseUsers
from ._subreddit import _DatabaseSubreddit
from ._comment import _DatabaseComments
from ._keystore import _DatabaseKeystore
from ._submission import _DatabaseSubmission
from ._notification import _DatabaseNotification
from ._stat import _DatabaseStats

log = discord_logging.get_logger()


class Database(
	_DatabaseSubscriptions,
	_DatabaseUsers,
	_DatabaseSubreddit,
	_DatabaseComments,
	_DatabaseKeystore,
	_DatabaseSubmission,
	_DatabaseNotification,
	_DatabaseStats
):
	def __init__(self, debug=False, publish=False):
		log.info(f"Initializing database class: debug={debug} publish={publish}")
		self.debug = debug
		self.engine = None
		self.init(debug, publish)

		_DatabaseSubscriptions.__init__(self)
		_DatabaseUsers.__init__(self)
		_DatabaseSubreddit.__init__(self)
		_DatabaseComments.__init__(self)
		_DatabaseKeystore.__init__(self)
		_DatabaseSubmission.__init__(self)
		_DatabaseNotification.__init__(self)
		_DatabaseStats.__init__(self)

	def init(self, debug, publish):
		if debug:
			self.engine = create_engine(f'sqlite:///:memory:')
		else:
			self.engine = create_engine(f'sqlite:///{static.DATABASE_NAME}')

		Session = sessionmaker(bind=self.engine)
		self.session = Session()

		if publish:
			Base.metadata.drop_all(self.engine)

		Base.metadata.create_all(self.engine)

		self.commit()

	def clean(self):
		start_time = time.perf_counter()
		deleted_comment_ids = []
		for comment in self.get_old_comments(utils.datetime_now() - timedelta(days=190)):
			deleted_comment_ids.append(comment.comment_id)
			self.delete_comment(comment)
		if not len(deleted_comment_ids):
			deleted_comment_ids.append("none")

		deleted_submission_ids = []
		for submission in self.get_old_orphan_submissions(utils.datetime_now() - timedelta(hours=48)):
			deleted_submission_ids.append(submission.submission_id)
			self.delete_submission(submission)
		if not len(deleted_submission_ids):
			deleted_submission_ids.append("none")

		deleted_users = []
		for user in self.get_orphan_users():
			deleted_users.append(f"{user.name}:{user.id}")
			self.delete_user(user)
		if not len(deleted_users):
			deleted_users.append("none")

		delta_time = time.perf_counter() - start_time
		log.info(
			f"Cleanup {' '.join(deleted_comment_ids)} : {' '.join(deleted_submission_ids)} : {' '.join(deleted_users)} in "
			f"{delta_time:.2} seconds")

	def backup(self):
		log.info("Backing up database")
		self.commit()
		self.close()

		if not os.path.exists(static.BACKUP_FOLDER_NAME):
			os.makedirs(static.BACKUP_FOLDER_NAME)

		copyfile(
			static.DATABASE_NAME,
			static.BACKUP_FOLDER_NAME + "/" + utils.datetime_now().strftime("%Y-%m-%d_%H-%M") + ".db")

		self.init(self.debug, False)

	def commit(self):
		self.session.commit()

	def close(self):
		self.commit()
		self.engine.dispose()
