"""
WSGI config for windmobile project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "windmobile.settings")


def application(environ, start_response):
    os.environ['DATABASE_URL'] = environ['DATABASE_URL']
    os.environ['WINDMOBILE_MONGO_URL'] = environ['WINDMOBILE_MONGO_URL']
    os.environ['DEBUG'] = environ.get('DEBUG', 'False')
    os.environ['ALLOWED_HOSTS'] = environ.get('ALLOWED_HOSTS', '*')
    return get_wsgi_application()(environ, start_response)
