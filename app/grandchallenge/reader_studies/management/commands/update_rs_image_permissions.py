from django.core.management import BaseCommand

from grandchallenge.cases.models import Image


class Command(BaseCommand):
    def handle(self, *args, **options):
        for c, image in enumerate(
            Image.objects.filter(
                componentinterfacevalue__display_sets__isnull=False
            ).distinct()
        ):
            self.stdout.write(c)
            image.update_viewer_groups_permissions()
