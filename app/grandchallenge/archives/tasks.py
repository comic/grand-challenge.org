from celery import shared_task

from grandchallenge.archives.models import Archive, ArchiveItem
from grandchallenge.cases.models import Image
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)


@shared_task
def add_images_to_archive(*, upload_session_pk, archive_pk):
    images = Image.objects.filter(origin_id=upload_session_pk)
    archive = Archive.objects.get(pk=archive_pk)
    # TODO: this should be configurable
    interface = ComponentInterface.objects.get(slug="generic-medical-image")

    for image in images:
        civ = ComponentInterfaceValue.objects.create(
            interface=interface, image=image
        )
        item = ArchiveItem.objects.create(archive=archive)
        item.values.set([civ])
