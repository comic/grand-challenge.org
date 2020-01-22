from os.path import basename

from django.apps import apps
from django.core.files import File
from django.core.files.storage import FileSystemStorage
from django.core.management import BaseCommand
from django.utils.module_loading import import_string

"""
algorithms.algorithm.logo grandchallenge.challenges.models.get_logo_path
challenges.challenge.logo grandchallenge.challenges.models.get_logo_path
challenges.externalchallenge.logo grandchallenge.challenges.models.get_logo_path
reader_studies.readerstudy.logo grandchallenge.challenges.models.get_logo_path
workstations.workstation.logo grandchallenge.challenges.models.get_logo_path
challenges.challenge.banner grandchallenge.challenges.models.get_banner_path
evaluation.submission.supplementary_file grandchallenge.evaluation.models.submission_supplementary_file_path
"""


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("field", type=str)
        parser.add_argument("upload_to", type=str)

    def handle(self, *args, **options):
        app_label, model_name, field_name = options["field"].split(".")

        Model = apps.get_model(  # noqa: N806
            app_label=app_label, model_name=model_name
        )
        upload_to = import_string(options["upload_to"])

        objects = Model.objects.all()
        old_storage = FileSystemStorage()

        for obj in objects:
            filefield = getattr(obj, field_name)

            try:
                _ = filefield.file
            except ValueError:
                print(f"No file for {obj}")
                continue

            filename = basename(filefield.name)
            new_path = upload_to(obj, filename)

            if old_storage.exists(
                filefield.name
            ) and not filefield.storage.exists(new_path):
                print(f"Migrating {filefield.url}")
                filefield.save(
                    filename, File(old_storage.open(filefield.name))
                )

            else:
                print(f"Not migrating {filefield.url}")
