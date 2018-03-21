#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "comic.settings")

    from django.core.management import execute_from_command_line

    current_path = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(os.path.join(current_path, 'grandchallenge'))

    execute_from_command_line(sys.argv)
