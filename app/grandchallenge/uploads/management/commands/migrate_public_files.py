import re
from html import unescape
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, SuspiciousFileOperation
from django.core.files import File
from django.core.files.storage import FileSystemStorage
from django.core.management import BaseCommand
from django.utils._os import safe_join

from grandchallenge.challenges.models import Challenge
from grandchallenge.pages.models import Page
from grandchallenge.uploads.models import PublicMedia


class Command(BaseCommand):
    def handle(self, *args, **options):
        old_storage = FileSystemStorage()

        for page in Page.objects.filter(html__contains="/media/"):
            print(f"Processing {page.get_absolute_url()}")

            matches = {
                m.group(0): {
                    "challenge_name": m.group(1),
                    "filepath": m.group(2),
                }
                for m in re.finditer(
                    r"/media/([^/]+)/((?:public_html|results/public)/[^\'^\"\s>]+)/?",
                    page.html,
                )
            }

            html_out = page.html

            for url, url_info in matches.items():
                challenge_name = url_info["challenge_name"]
                filepath = url_info["filepath"].strip("/")

                print(f"  > Replacing {url}")

                try:
                    challenge = Challenge.objects.get(
                        short_name__iexact=challenge_name
                    )
                except ObjectDoesNotExist:
                    print(f"    >> Could not find challenge {challenge_name}")
                    continue

                try:
                    document_root = safe_join(
                        settings.MEDIA_ROOT, challenge.short_name
                    )
                    fullpath = safe_join(document_root, filepath)
                    if not old_storage.exists(fullpath):
                        fullpath = safe_join(document_root, unescape(filepath))
                except SuspiciousFileOperation:
                    print(f"    >> Path not in MEDIA_ROOT {filepath}")
                    continue

                if old_storage.exists(fullpath):
                    new_file = PublicMedia.objects.create(challenge=challenge,)
                    new_file.file = File(
                        old_storage.open(fullpath, "rb"),
                        name=Path(fullpath).name,
                    )
                    new_file.save()
                else:
                    print(f"    >> Could not find {fullpath}")
                    continue

                html_out = html_out.replace(url, new_file.file.url)

                print("    Done")

            page.html = html_out
            page.save()

            print(f"Saved {page.get_absolute_url()}")
