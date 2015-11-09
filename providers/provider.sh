#!/usr/bin/env bash

# Makes sure we exit if flock fails.
set -e

PROVIDER=$1
(
  flock -n 200 || exit 1

  /home/windmobile/.virtualenvs/windmobile-provider/bin/envdir /home/windmobile/WindMobile2-Server/envdir /home/windmobile/.virtualenvs/windmobile-provider/bin/python /home/windmobile/WindMobile2-Server/providers/$PROVIDER.py 1>/dev/null 2>>/var/log/windmobile/$PROVIDER.err

) 200>/home/windmobile/WindMobile2-Server/$PROVIDER.lock
