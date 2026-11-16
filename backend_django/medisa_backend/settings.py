"""
Django settings for medisa_backend project.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'medisa-healthcare-secret-key-production-ready-2026')

DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 't')

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party
    'corsheaders',
    'rest_framework',
    # App
    'medisa_api',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'medisa_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'medisa_backend.wsgi.application'

# Database Configuration
if os.getenv('DB_ENGINE') == 'mysql' or (os.getenv('DB_HOST') and os.getenv('DB_NAME') and os.getenv('USE_MYSQL')):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.getenv('DB_NAME', 'mediai_db'),
            'USER': os.getenv('DB_USER', 'root'),
            'PASSWORD': os.getenv('DB_PASS', 'password'),
            'HOST': os.getenv('DB_HOST', '127.0.0.1'),
            'PORT': os.getenv('DB_PORT', '3306'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/uploads/'
MEDIA_ROOT = BASE_DIR / 'uploads'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS configuration
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

CSRF_TRUSTED_ORIGINS = [
    'https://*.onrender.com',
    'https://*.vercel.app',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
]
