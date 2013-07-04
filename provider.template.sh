#!/bin/bash

# Makes sure we exit if flock fails.
set -e

PROVIDER=provider
(
  flock -n 200 || exit 1

  envdir /root/WindMobile2-Server/envdir /root/.virtualenvs/windmobile/bin/python /root/WindMobile2-Server/providers/$PROVIDER.py 1>/dev/null 2>/var/log/windmobile/$PROVIDER.err

) 200>/root/WindMobile2-Server/$PROVIDER.lock
