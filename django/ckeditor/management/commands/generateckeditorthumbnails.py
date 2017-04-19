from __future__ import print_function

import os

from django.core.management.base import NoArgsCommand

from ckeditor.views import create_thumbnail, get_image_files, \
    get_thumb_filename


class Command(NoArgsCommand):
    """
    Creates thumbnail files for the CKEditor file image browser.
    Useful if starting to use django-ckeditor with existing images.
    """
    def handle_noargs(self, **options):
        for image in get_image_files():
            if not os.path.isfile(get_thumb_filename(image)):
                print("Creating thumbnail for %s" % image)
                try:
                    create_thumbnail(image)
                except Exception as e:
                    print("Couldn't create thumbnail for %s: %s" % (image, e))
        print("Finished")
