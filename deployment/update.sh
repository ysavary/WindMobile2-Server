#!/usr/bin/env bash

su - windmobile -c "cd /home/windmobile/WindMobile2-Server; git fetch; git pull"
su - windmobile -c "/home/windmobile/.virtualenvs/windmobile-provider/bin/pip install -r /home/windmobile/WindMobile2-Server/providers/requirements.txt"
su - windmobile -c "/home/windmobile/.virtualenvs/windmobile-django/bin/pip install -r /home/windmobile/WindMobile2-Server/requirements.txt"
su - windmobile -c "/home/windmobile/.virtualenvs/windmobile-django/bin/python /home/windmobile/WindMobile2-Server/manage.py collectstatic --noinput"
apachectl -k graceful
