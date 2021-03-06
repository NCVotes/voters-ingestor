import os

from ncvoter.settings import *  # noqa: F403, F401


DEBUG = False
SECRET_KEY = os.environ['SECRET_KEY']
DOMAIN = os.environ['DOMAIN']
ADDITIONAL_DOMAINS = os.environ.get('ADDITIONAL_DOMAINS')
ALLOWED_HOSTS = [DOMAIN]
# if ADDITIONAL_DOMAINS is set, then it will be a comma-delimited list of domains
if ADDITIONAL_DOMAINS:
    for domain in ADDITIONAL_DOMAINS.split(','):
        ALLOWED_HOSTS.append(domain)
ENVIRONMENT = "production"

# remove debug toolbar
INSTALLED_APPS.pop(INSTALLED_APPS.index('debug_toolbar'))  # noqa: F405
MIDDLEWARE.pop(MIDDLEWARE.index('debug_toolbar.middleware.DebugToolbarMiddleware'))  # noqa: F405

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
