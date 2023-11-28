from celery import chain, group, shared_task
from django.conf import settings
from django.db import transaction
from django.db.transaction import on_commit

from grandchallenge.archives.models import Archive, ArchiveItem
from grandchallenge.cases.models import Image, RawImageUploadSession
from grandchallenge.cases.tasks import build_images
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.components.tasks import (
    add_image_to_component_interface_value,
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


def update_archive_item_update_kwargs(
    instance,
    interface,
    civ_pks_to_add,
    upload_pks,
    value=None,
    image=None,
    user_upload=None,
    upload_session=None,
):
    """Given an interface and a value/image/user_upload/upload_session, this task determines whether to create a new CIV for the specified archive item instance with those values, and whether to delete any existing CIVs from the archive item.

    It appends the respective CIV pk(s) to the set of to be added and removed civs and returns those. If an
    upload_session is specified, it also appends the session pk together with the new civ pk to the list of to be
    processed images.

    """
    with transaction.atomic():
        if interface.is_image_kind:
            if image:
                civ, created = ComponentInterfaceValue.objects.get_or_create(
                    interface=interface, image=image
                )
                if created:
                    civ.full_clean()
                    civ.save()
            elif upload_session:
                civ = ComponentInterfaceValue.objects.create(
                    interface=interface
                )
                upload_pks[civ.pk] = upload_session.pk
                civ.save()
            civ_pks_to_add.add(civ.pk)
        elif interface.requires_file:
            civ = ComponentInterfaceValue.objects.create(interface=interface)
            user_upload.copy_object(to_field=civ.file)
            civ.full_clean()
            civ.save()
            user_upload.delete()
            civ_pks_to_add.add(civ.pk)
        else:
            civ = interface.create_instance(value=value)
            civ_pks_to_add.add(civ.pk)


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-micro-short"])
def update_archive_item_values(*, archive_item_pk, civ_pks_to_add):
    instance = ArchiveItem.objects.get(pk=archive_item_pk)
    civ_pks_to_remove = []
    civs = ComponentInterfaceValue.objects.filter(pk__in=civ_pks_to_add)
    for civ in civs:
        if instance.values.filter(interface=civ.interface.pk).exists():
            for civ_pk in instance.values.filter(
                interface=civ.interface.pk
            ).values_list("pk", flat=True):
                civ_pks_to_remove.append(civ_pk)
        # for images, check if there are any CIVs with the provided image
        if civ.interface.is_image_kind:
            if instance.values.filter(image=civ.image).exists():
                for civ_pk in instance.values.filter(
                    image=civ.image
                ).values_list("pk", flat=True):
                    civ_pks_to_remove.append(civ_pk)

    with transaction.atomic():
        instance.values.remove(*civ_pks_to_remove)
        instance.values.add(*civ_pks_to_add)


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-micro-short"])
def start_archive_item_update_tasks(
    archive_item_pk, civ_pks_to_add, upload_pks
):
    tasks = update_archive_item_values.signature(
        kwargs={
            "archive_item_pk": archive_item_pk,
            "civ_pks_to_add": civ_pks_to_add,
        },
        immutable=True,
    )

    if len(upload_pks) > 0:
        image_tasks = group(
            # Chords and iterator groups are broken in Celery, send a list
            # instead, see https://github.com/celery/celery/issues/7285
            [
                chain(
                    build_images.signature(
                        kwargs={"upload_session_pk": upload_pk}
                    ),
                    add_image_to_component_interface_value.signature(
                        kwargs={
                            "component_interface_value_pk": civ_pk,
                            "upload_session_pk": upload_pk,
                        },
                        immutable=True,
                    ),
                )
                for civ_pk, upload_pk in upload_pks.items()
            ]
        )
        tasks = group(image_tasks, tasks)

    with transaction.atomic():
        on_commit(tasks.apply_async)
