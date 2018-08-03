# -*- coding: utf-8 -*-
import os

from django.conf import settings
from django.core.management import BaseCommand

from grandchallenge.challenges.models import ExternalChallenge
from grandchallenge.core.dataproviders.ProjectExcelReader import \
    ProjectExcelReader


class Command(BaseCommand):

    def handle(self, *args, **options):
        filepath = os.path.join(
            settings.MEDIA_ROOT,
            settings.MAIN_PROJECT_NAME,
            "challengestats_UNUSED.xls",
        )

        reader = ProjectExcelReader(filepath, 'Challenges')

        projectlinks = reader.get_project_links()

        for projectlink in projectlinks:
            self.add_project_link_to_db(projectlink)

    def add_project_link_to_db(self, projectlink):

        print(f"Updating {projectlink.params['abreviation']}")

        challenge = ExternalChallenge.objects.get(
                short_name=projectlink.params["abreviation"]
            )

        # Update challenge with params here

        challenge.save()
