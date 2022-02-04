from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.db.transaction import on_commit

from grandchallenge.archives.models import Archive, ArchiveItem
from grandchallenge.cases.models import Image
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.components.tasks import (
    add_images_to_component_interface_value,
)


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-micro-short"])
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


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-micro-short"])
def add_images_to_archive_item(
    *, upload_session_pk, archive_item_pk, interface_pk
):
    archive_item = ArchiveItem.objects.get(pk=archive_item_pk)
    interface = ComponentInterface.objects.get(pk=interface_pk)

    with transaction.atomic():
        archive_item.values.remove(
            *archive_item.values.filter(interface=interface)
        )
        new_civ = ComponentInterfaceValue.objects.create(interface=interface)
        archive_item.values.add(new_civ)

        on_commit(
            add_images_to_component_interface_value.signature(
                kwargs={
                    "component_interface_value_pk": new_civ.pk,
                    "upload_session_pk": upload_session_pk,
                },
                immutable=True,
            ).apply_async
        )


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-micro-short"])
def update_archive_item_values(
    *, archive_item_pk, civ_pks_to_remove, civ_pks_to_add,
):
    with transaction.atomic():
        archive_item = ArchiveItem.objects.get(pk=archive_item_pk)
        archive_item.values.remove(*civ_pks_to_remove)
        archive_item.values.add(*civ_pks_to_add)
