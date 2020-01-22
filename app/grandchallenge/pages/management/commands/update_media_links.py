import re

from django.core.management import BaseCommand

from grandchallenge.pages.models import Page


class Command(BaseCommand):
    def handle(self, *args, **options):
        for p in Page.objects.filter(html__contains="/serve/"):
            p.html = re.sub(r"/site/([^/]+)/serve/", r"/media/\1/", p.html)
            p.save()
