from django.core.management import BaseCommand

from grandchallenge.reader_studies.models import ReaderStudy
from grandchallenge.workstations.models import Workstation


class Command(BaseCommand):
    def handle(self, *args, **options):
        new_ws = Workstation.objects.get(slug="cirrus-core")
        old_ws = Workstation.objects.get(slug="cirrus-core-previous-release")
        ReaderStudy.objects.filter(workstation=new_ws).update(
            workstation=old_ws
        )
