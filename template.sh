#!/bin/bash

# Makes sure we exit if flock fails.
set -e

(
  flock -n 200 || exit 1

  envdir /home/WindMobile2-Server/envdir python /home/WindMobile2-Server/providers/provider.py 2>/var/log/windmobile/provider.err

) 200>/home/WindMobile2-Server/provider.lock
