from pathlib import Path
from oscar.defaults import *
import oscar

SECRET_KEY = 'notverysecret'
DEBUG = True
ROOT_URLCONF = 'urls'
STATIC_URL = '/static/'
USE_TZ = True
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent


HAYSTACK_CONNECTIONS = {"default": {}}


INSTALLED_APPS = [
    'oscar_pg_search.apps.PgSearchConfig',
] + [x for x in oscar.INSTALLED_APPS
     if x != 'oscar.apps.search.apps.SearchConfig']


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'mydatabase',
    }
}


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
