from celery import shared_task

from grandchallenge.algorithms.tasks import (
    add_images_to_component_interface_value,
)
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
def add_images_to_archive_item(
    *, upload_session_pk, archive_item_pk, interface_pk=None
):
    archive_item = ArchiveItem.objects.get(pk=archive_item_pk)
    interface = ComponentInterface.objects.get(pk=interface_pk)

    civ_pks_to_remove = set()
    civ_pks_to_add = set()

    civ = archive_item.values.filter(interface=interface).first()
    if civ:
        civ_pks_to_remove.add(civ.pk)

    civ = ComponentInterfaceValue.objects.create(interface=interface)
    civ_pks_to_add.add(civ)

    add_images_to_component_interface_value(
        component_interface_value_pk=civ.pk,
        upload_session_pk=upload_session_pk,
    )
    update_archive_item_values(
        archive_item_pk=archive_item_pk,
        civ_pks_to_remove=list(civ_pks_to_remove),
        civ_pks_to_add=list(civ_pks_to_add),
    )


@shared_task
def update_archive_item_values(
    *, archive_item_pk, civ_pks_to_remove, civ_pks_to_add,
):
    archive_item = ArchiveItem.objects.get(pk=archive_item_pk)
    archive_item.values.remove(*civ_pks_to_remove)
    archive_item.values.add(*civ_pks_to_add)
