#!/usr/bin/env python
import os
import sys

if __name__ == u"__main__":
    os.environ.setdefault(u"DJANGO_SETTINGS_MODULE", u"tennis.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
