#!/usr/bin/env bash

su - windmobile -c "cd /home/windmobile/WindMobile2-Server; git pull"
su - windmobile -c "envdir /home/windmobile/WindMobile2-Server/envdir .virtualenvs/windmobile-django/bin/django-admin.py collectstatic --noinput"
apachectl -k graceful
