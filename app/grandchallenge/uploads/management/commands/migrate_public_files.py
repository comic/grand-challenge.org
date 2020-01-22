import re

from django.core.management import BaseCommand

from grandchallenge.pages.models import Page


class Command(BaseCommand):
    def handle(self, *args, **options):
        for page in Page.objects.filter(html__contains="/media/"):
            file_sources = re.findall(
                r"/media/([^/])+/public_html/[^\'^\"\s>]+", page.html
            )

            for file_source in file_sources:
                print(file_source)
