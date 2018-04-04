import os

from ncvoter.settings import *  # noqa: F403, F401


DEBUG = False
SECRET_KEY = os.environ['SECRET_KEY']
DOMAIN = os.environ['DOMAIN']
ALLOWED_HOSTS = [DOMAIN]


# Database values
DB_NAME = os.environ['DB_NAME']
DB_USER = os.environ['DB_USER']
DB_HOST = os.environ['DB_HOST']
DB_PORT = os.environ['DB_PORT']
DB_PASSWORD = os.environ['DB_PASSWORD']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': DB_NAME,
        'USER': DB_USER,
        'PASSWORD': DB_PASSWORD,
        'HOST': DB_HOST,
        'PORT': DB_PORT,
    }
}

NCVOTER_DOWNLOAD_PATH = "/voter-data/ncvoter"
NCVHIS_DOWNLOAD_PATH = "/voter-data/ncvhis"

if os.getenv('SENTRY_DSN'):
    import raven
    RAVEN_CONFIG = {
        'dsn': os.getenv('SENTRY_DSN'),
        'release': raven.fetch_git_sha(os.path.dirname(os.pardir)),
        'name': 'NCVotes',
        'processors': (
            'raven.processors.SanitizePasswordsProcessor',
        )
    }
