import os

TESTS_PATH = os.path.dirname(os.path.realpath(__file__))

DATABASE_ENGINE = 'django.db.backends.sqlite3'
DATABASE_NAME = os.path.join(TESTS_PATH, 'chained_tests.db')

INSTALLED_APPS = {
	'chained',
	'chained.tests.server',
}