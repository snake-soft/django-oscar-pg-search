import os, pathlib, oscar
from oscar.defaults import *


SECRET_KEY = 'notverysecret'
DEBUG = True
ROOT_URLCONF = 'urls'
STATIC_URL = '/static/'
USE_TZ = False
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent.parent

HAYSTACK_CONNECTIONS = {"default": {}}


INSTALLED_APPS = [
    'oscar_pg_search.apps.PgSearchConfig',
] + [x for x in oscar.INSTALLED_APPS
     if x != 'oscar.apps.search.apps.SearchConfig']


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'postgres'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASS', 'postgres'),
        'HOST': '127.0.0.1',
        'PORT': '5432',
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
