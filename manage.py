#!/usr/bin/env python
import os
import sys
import envdir

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "windmobile.settings")
    envdir.read('envdir')

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
