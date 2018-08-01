# -*- coding: utf-8 -*-
import datetime
import os
import traceback
from urllib.error import HTTPError
from urllib.request import urlopen

import pytz
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile
from django.core.management import BaseCommand

from grandchallenge.challenges.models import ExternalChallenge
from grandchallenge.core.dataproviders.ProjectExcelReader import \
    ProjectExcelReader


class Command(BaseCommand):

    def handle(self, *args, **options):
        filepath = os.path.join(
            settings.MEDIA_ROOT,
            settings.MAIN_PROJECT_NAME,
            #"/",
            #"app",
            #"tests",
            #"dataproviders_tests",
            #"resources",
            settings.EXTERNAL_PROJECTS_FILE,
        )

        reader = ProjectExcelReader(filepath, 'Challenges')

        try:
            projectlinks = reader.get_project_links()

        except IOError:
            print(
                "Could not read any projectlink information from"
                " '%s' returning empty list. trace: %s " %
                (filepath, traceback.format_exc())
            )
            projectlinks = []

        projectlinks_clean = []

        for projectlink in projectlinks:
            projectlinks_clean.append(
                self.clean_grand_challenge_projectlink(projectlink)
            )

        for projectlink in projectlinks:
            self.add_project_link_to_db(projectlink)

    def add_project_link_to_db(self, projectlink):

        admin_user = get_user_model().objects.get(username="jamesmeakin")

        try:
            challenge = ExternalChallenge.objects.get(
                short_name=projectlink.params["abreviation"]
            )
        except ObjectDoesNotExist:
            challenge = ExternalChallenge.objects.create(
                short_name=projectlink.params["abreviation"]
            )

        challenge.creator = admin_user
        challenge.title = projectlink.params["title"]
        challenge.description = str(projectlink.params["description"])
        challenge.homepage = projectlink.params["URL"]

        if projectlink.params["workshop date"]:
            challenge.workshop_date = projectlink.params["workshop date"]

        challenge.submission_page = projectlink.params["submission URL"]
        challenge.event_name = projectlink.params["event name"]
        challenge.event_url = projectlink.params["event URL"]

        challenge.hidden = True

        challenge.publication_journal_name = projectlink.params[
            "overview article journal"]
        challenge.publication_url = projectlink.params["overview article url"]

        challenge.is_open_for_submissions = True if projectlink.params[
            "open for submission"] else False

        try:
            challenge.number_of_submissions = int(projectlink.params["submitted results"])
        except ValueError:
            pass

        if projectlink.params["last submission date"]:
            challenge.last_submission_date = projectlink.params["last submission date"]

        challenge.offers_data_download = True if projectlink.params["data download"] else False

        try:
            challenge.number_of_downloads = int(projectlink.params["dataset downloads"])
        except ValueError:
            pass

        challenge.created_at = datetime.datetime(projectlink.params["year"], 1,
                                                 1, 13, 0, 0, 0, pytz.UTC)

        if not challenge.logo:
            try:
                logo = f"https://grand-challenges.grand-challenge.org/serve/public_html/images/all_challenges/{challenge.short_name.lower()}.png/"
                img = urlopen(logo).read()
                challenge.logo = ContentFile(img,
                                             f"{challenge.short_name.lower()}.png")
            except HTTPError:
                print(f"Could not find logo for {challenge.short_name}")
                print(f"{logo}")

        challenge.save()

    def clean_grand_challenge_projectlink(self, projectlink):
        """ Specifically for the grand challenges excel file, make everything strings,
        change weird values, like having more downloads than registered users
        """
        # cast all to int as there are no float values in the excel file, I'd
        # rather do this here than change the way excelreader reads them in
        for key in projectlink.params.keys():
            param = projectlink.params[key]
            if type(param) == float:
                projectlink.params[key] = int(param)
        if projectlink.params["last submission date"]:
            projectlink.params[
                "last submission date"
            ] = self.determine_project_date(
                projectlink.params["last submission date"]
            )
        if projectlink.params["workshop date"]:
            projectlink.params["workshop date"] = self.determine_project_date(
                projectlink.params["workshop date"]
            )
        return projectlink

    def determine_project_date(self, datefloat):
        """ Parse float (e.g. 20130425.0) read by excelreader into python date

        """
        date = str(datefloat)
        parsed = datetime.datetime(
            year=int(date[0:4]), month=int(date[4:6]), day=int(date[6:8])
        )
        return parsed
