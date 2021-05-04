from django.core.management import BaseCommand

from grandchallenge.archives.models import Archive, ArchiveItem
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)


class Command(BaseCommand):
    def handle(self, *args, **options):
        interface = ComponentInterface.objects.get(
            slug="generic-medical-image"
        )
        for archive in Archive.objects.all():
            for image in archive.images.all():
                civ, _ = ComponentInterfaceValue.objects.get_or_create(
                    interface=interface, image=image
                )
                if not ArchiveItem.objects.filter(
                    archive=archive, values__in=[civ.pk]
                ).exists():
                    item = ArchiveItem.objects.create(archive=archive)
                    item.values.set([civ])
