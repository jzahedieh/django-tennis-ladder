# Django settings for tennis project.
import os
from distutils.util import strtobool
from dotenv import load_dotenv

# Load local environment variables from .env.local file
load_dotenv('.env.local')

SETTINGS_DIR = os.path.abspath(os.path.dirname(__file__))

DEBUG = os.environ.get("DJANGO_DEBUG", "False") == "True"

ADMINS = (
    ('Admin User', 'admin@highgate-ladder.co.uk'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get("SQL_DATABASE", "tennis"),
        'USER':  os.environ.get("SQL_USER", "root"),
        'PASSWORD': os.environ.get("SQL_PASSWORD", ""),
        'HOST':  os.environ.get("SQL_HOST", ""),
        'PORT': os.environ.get("SQL_PORT", "3306"),
        'OPTIONS': {
            'autocommit': True,
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            # insert your TEMPLATE_DIRS here
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                # Insert your TEMPLATE_CONTEXT_PROCESSORS here or use this
                # list if you haven't customized them:
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.template.context_processors.request',
                'django.contrib.messages.context_processors.messages',
                'django.contrib.auth.context_processors.auth',
                'ladder.context_processors.navigation',
                'ladder.context_processors.umami_context',
            ],
        },
    },
]

REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly'
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 100
}

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = os.environ.get(
    "DJANGO_ALLOWED_HOSTS",
    "highgate-ladder.co.uk,www.highgate-ladder.co.uk"
).split(",")

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'Europe/London'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-uk'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = False

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = False

# Store view messages in the session
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'


# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = os.path.abspath(os.path.join(SETTINGS_DIR, '..', 'static'))

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/static/'

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    #    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# ManifestStaticFilesStorage hashes assets for versioning
# which ensures all users see the same content
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

# Make this unique, and don't share it with anybody.
SECRET_KEY = os.environ["SECRET_KEY"]

MIDDLEWARE = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

LOGIN_REDIRECT_URL = '/result/entry/'
LOGOUT_REDIRECT_URL = '/'

ROOT_URLCONF = 'tennis.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'tennis.wsgi.application'

INSTALLED_APPS = (
    'rest_framework',
    'ladder',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
)

if DEBUG:
    INSTALLED_APPS = ('debug_toolbar',) + INSTALLED_APPS
    MIDDLEWARE = ('debug_toolbar.middleware.DebugToolbarMiddleware',) + MIDDLEWARE
    INTERNAL_IPS = ('127.0.0.1',)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

TEST_RUNNER = 'django.test.runner.DiscoverRunner'

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

EMAIL_PORT = os.environ.get('EMAIL_PORT')
EMAIL_HOST = os.environ.get('EMAIL_HOST')
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.environ.get('EMAIL_DEFAULT_FROM')
SERVER_EMAIL = os.environ.get('EMAIL_SERVER_FROM')
SUBSCRIPTION_EMAIL = os.environ.get('SUBSCRIPTION_EMAIL')
EMAIL_USE_TLS = bool(strtobool(os.environ['EMAIL_USE_TLS']))
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
UMAMI_WEBSITE_ID = os.environ.get('UMAMI_WEBSITE_ID', '')

INTERNAL_IPS = (
    '127.0.0.1',
    '0.0.0.0',
    '172.18.0.1',
    '172.21.0.1',
    '172.23.0.1'
)

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

CSRF_TRUSTED_ORIGINS = [
    "https://highgate-ladder.co.uk",
    "https://www.highgate-ladder.co.uk",
]

# Add additional domains from environment variable
additional_domains = os.environ.get('CSRF_ADDITIONAL_DOMAINS', '')
if additional_domains:
    # Split by comma and strip whitespace, add https:// prefix if not present
    for domain in additional_domains.split(','):
        domain = domain.strip()
        if domain:
            if not domain.startswith(('http://', 'https://')):
                domain = f"https://{domain}"
            CSRF_TRUSTED_ORIGINS.append(domain)
