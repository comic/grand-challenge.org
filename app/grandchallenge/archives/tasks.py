from django.db import transaction
from django.db.transaction import on_commit

from grandchallenge.archives.models import Archive, ArchiveItem
from grandchallenge.cases.models import Image, RawImageUploadSession
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.components.tasks import (
    add_image_to_component_interface_value,
)
from grandchallenge.core.celery import acks_late_micro_short_task


@acks_late_micro_short_task
def add_images_to_archive(*, upload_session_pk, archive_pk, interface_pk=None):
    with transaction.atomic():
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


@acks_late_micro_short_task
def add_images_to_archive_item(
    *, upload_session_pk, archive_item_pk, interface_pk
):
    archive_item = ArchiveItem.objects.get(pk=archive_item_pk)
    interface = ComponentInterface.objects.get(pk=interface_pk)
    session = RawImageUploadSession.objects.get(pk=upload_session_pk)

    if archive_item.values.filter(
        interface=interface, image__in=session.image_set.all()
    ).exists():
        return

    with transaction.atomic():
        archive_item.values.remove(
            *archive_item.values.filter(interface=interface)
        )
        new_civ = ComponentInterfaceValue.objects.create(interface=interface)
        archive_item.values.add(new_civ)

        on_commit(
            add_image_to_component_interface_value.signature(
                kwargs={
                    "component_interface_value_pk": new_civ.pk,
                    "upload_session_pk": upload_session_pk,
                },
                immutable=True,
            ).apply_async
        )
