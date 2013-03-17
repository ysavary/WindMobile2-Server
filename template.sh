#!/bin/sh

# Makes sure we exit if flock fails.
set -e

(
  # Wait for lock on /var/lock/.myscript.exclusivelock (fd 200) for 5 seconds
  flock -x -w 5 200

  # Do stuff
  cd /home/windmobile
  python jdc.py 2> log/jdc.err

) 200>/home/windmobile/jdc.lock
