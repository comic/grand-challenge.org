# -*- coding: utf-8 -*-
import os

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management import BaseCommand

from grandchallenge.challenges.models import Challenge


class Command(BaseCommand):

    def handle(self, *args, **options):
        challenges = Challenge.objects.all()

        for challenge in challenges:

            print(f"Updating {challenge.short_name}.")

            if not challenge.logo:
                logo = os.path.join(
                    settings.MEDIA_ROOT,
                    challenge.short_name,
                    challenge.logo_path,
                )

                try:
                    with open(logo, 'rb') as f:
                        img = f.read()

                    challenge.logo = ContentFile(img, os.path.split(logo)[1].lower())

                    challenge.save()

                except Exception:
                    print(f">>> Could not import logo for {challenge.short_name}.")

            if not challenge.banner:
                banner = os.path.join(
                    settings.MEDIA_ROOT,
                    challenge.short_name,
                    challenge.header_image,
                )

                try:
                    with open(banner, 'rb') as f:
                        img = f.read()

                    challenge.banner = ContentFile(img, os.path.split(banner)[1].lower())

                    challenge.save()

                except Exception:
                    print(f">>> Could not import banner for {challenge.short_name}.")
