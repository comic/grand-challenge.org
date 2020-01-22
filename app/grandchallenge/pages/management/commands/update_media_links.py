import re

from django.core.management import BaseCommand

from grandchallenge.pages.models import Page


class Command(BaseCommand):
    def handle(self, *args, **options):
        for p in Page.objects.filter(html__contains="/serve/"):
            print(f"Updating serve in {p.get_absolute_url()}")
            p.html = re.sub(r"/site/([^/]+)/serve/", r"/media/\1/", p.html)
            p.save()

        for p in Page.objects.filter(html__contains="org/media/"):
            print(f"Updating media in {p.get_absolute_url()}")
            p.html = re.sub(
                r"https?://[^.]+.grand-challenge.org/media/", "/media/", p.html
            )
            p.html = re.sub(
                r"https?://grand-challenge.org/media/", "/media/", p.html
            )
            p.save()
