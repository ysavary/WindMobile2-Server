"""
WSGI config for windmobile project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

try:
    import newrelic.agent
    here = os.path.dirname(__file__)
    newrelic.agent.initialize(os.path.join(here, 'newrelic.ini'))
except:
    pass

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "windmobile.settings")

application = get_wsgi_application()
