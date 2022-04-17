from django.core.management import BaseCommand

from grandchallenge.cases.models import Image


class Command(BaseCommand):
    def handle(self, *args, **options):
        images = Image.objects.filter(
            componentinterfacevalue__display_sets__isnull=False
        ).distinct()
        for c, image in enumerate(images):
            if c % 100 == 0:
                self.stdout.write(f"Updating {c} / {images.count()}")

            image.update_viewer_groups_permissions()
