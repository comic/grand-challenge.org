from celery import shared_task

from grandchallenge.archives.models import Archive, ArchiveItem
from grandchallenge.cases.models import Image
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)


@shared_task
def add_images_to_archive(*, upload_session_pk, archive_pk, interface_pk=None):
    images = Image.objects.filter(origin_id=upload_session_pk)
    archive = Archive.objects.get(pk=archive_pk)
    if interface_pk is not None:
        interface = ComponentInterface.objects.get(pk=interface_pk)
    else:
        interface = ComponentInterface.objects.get(
            slug="generic-medical-image"
        )

    for image in images:
        civ = ComponentInterfaceValue.objects.filter(
            interface=interface, image=image
        ).first()
        if civ is None:
            civ = ComponentInterfaceValue.objects.create(
                interface=interface, image=image
            )
        if ArchiveItem.objects.filter(
            archive=archive, values__in=[civ.pk]
        ).exists():
            continue
        item = ArchiveItem.objects.create(archive=archive)
        item.values.set([civ])


@shared_task
def add_values_to_archive_item(*, archive_item_pk, civ_pks):
    archive_item = ArchiveItem.objects.get(pk=archive_item_pk)
    archive_item.values.add(*civ_pks)


@shared_task
def clear_values_from_archive_item(*, archive_item_pk):
    archive_item = ArchiveItem.objects.get(pk=archive_item_pk)
    archive_item.values.clear()
