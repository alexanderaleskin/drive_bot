import os
from celery.schedules import crontab
from copy import deepcopy
from django.utils.translation import gettext_lazy as _
import environ
env = environ.Env()

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env.str('WEB_SECRET_KEY', default='123456789')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool('DJANGO_DEBUG', default=True)
HOST = env.str('WEB_HOST', default='http://127.0.0.1:8000')

ALLOWED_HOSTS = ['*']
AUTH_USER_MODEL = 'base.User'

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # 'rangefilter',
    'django_celery_beat',
    'django_json_widget',
    'telegram_django_bot.apps.TelegramDjangoBotConfig',
    'base',
]

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'django_requests': {
            'level': 'ERROR',
            # 'filters': ['require_debug_false'],
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': env.str('LOG_DJANGO', default='../dj_log.log'),
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 10,
        },
    },
    'loggers': {
        'django': {
            'handlers': ['django_requests'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'bot_conf.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')]
        ,
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

WSGI_APPLICATION = 'bot_conf.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

if env.str('DB_HOST', default=''):
    DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.postgresql',
           'NAME': env.str('DB_NAME', default='tmp'),
           'USER': env.str('DB_USER', default='tmp'),
           'PASSWORD': env.str('DB_PASSWORD', default='1234'),
           'HOST': env.str('DB_HOST', default='localhost'),
           'PORT': '5432',
       }
    }
else:
    DATABASES = {
        'default': {
             'ENGINE': 'django.db.backends.sqlite3',
             'NAME': os.path.join(BASE_DIR, '../db.sqlite3'),
         }
     }


# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGE_CODE = 'en'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

LANGUAGES = [
    # ('ru', _('Russian')),
    ('en', _('English'))
]

LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale')
]



REDIS_HOST = env.str('REDIS_HOST', default='localhost')
CELERY_BROKER_URL = 'redis://' + REDIS_HOST + ':6379'
CELERY_RESULT_BACKEND = 'redis://' + REDIS_HOST + ':6379'
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
# CELERYD_CONCURRENCY = 2
# CELERYD_PREFETCH_MULTIPLIER = 1
BACKEND_QUEUE = env.str('BACKEND_QUEUE', default='backend_queue')

CELERY_TASK_DEFAULT_QUEUE = BACKEND_QUEUE

CELERY_QUEUES = {
    BACKEND_QUEUE: {
        "exchange": BACKEND_QUEUE,
        "routing_key": BACKEND_QUEUE,
    }
}

BEAT_SCHEDULE = {
    # 'task-create_triggers': {
    #     'task': 'telegram_django_bot.tasks.create_triggers',
    #     'schedule': crontab(minute='*/12'),
    #     'options': {'queue': BACKEND_QUEUE}
    # },
}

CELERY_BEAT_SCHEDULE = deepcopy(BEAT_SCHEDULE)



# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/

STATIC_URL = '/static/'
MEDIA_ROOT = '/web/media/'
STATIC_ROOT = '/web/static/'


TELEGRAM_TOKEN = env.str('TELEGRAM_TOKEN', default='')
MAIN_BOT_USERNAME = os.environ.get('TELEGRAM_BOT_NAME')
TELEGRAM_LOG = env.str('TELEGRAM_LOG', default='/web/logs/bot.log')

TELEGRAM_ROOT_UTRLCONF = 'bot_conf.utrls'


TELEGRAM_BOT_MAIN_MENU_CALLBACK = 'main_menu'  # usually you need return button to main menu

# TIME_FORMAT = '%H:%M'


