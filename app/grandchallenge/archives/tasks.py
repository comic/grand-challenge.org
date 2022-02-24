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
    InterfaceKind,
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
    *, archive_item_pk, civ_pks_to_remove, civ_pks_to_add
):
    with transaction.atomic():
        archive_item = ArchiveItem.objects.get(pk=archive_item_pk)
        archive_item.values.remove(*civ_pks_to_remove)
        archive_item.values.add(*civ_pks_to_add)


def update_archive_item_update_kwargs(
    instance,
    interface,
    civ_pks_to_add,
    civ_pks_to_remove,
    upload_pks,
    value=None,
    image=None,
    user_upload=None,
    upload_session=None,
):
    """
    Given an interface and a value/image/user_upload/upload_session, this task
    determines whether to create a new CIV for the specified archive item instance
    with those values, and whether to delete any existing CIVs from the archive item.
    It appends the respective CIV pk(s) to the set of to be added and removed
    civs and returns those. If an upload_session is specified,
    it also appends the session pk together with the new civ pk to the list of
    to be processed images.
    """
    if instance.values.filter(interface=interface.pk).exists():
        civ_pks_to_remove.add(
            *instance.values.filter(interface=interface.pk).values_list(
                "pk", flat=True
            )
        )
    else:
        # for images, check if there are any CIVs with the provided image
        if interface.kind in InterfaceKind.interface_type_image():
            if instance.values.filter(image=image).exists():
                civ_pks_to_remove.add(
                    *instance.values.filter(image=image).values_list(
                        "pk", flat=True
                    )
                )

    with transaction.atomic():
        if interface.kind in InterfaceKind.interface_type_image():
            civ = ComponentInterfaceValue.objects.create(interface=interface)
            if image:
                civ.image = image
                civ.full_clean()
            elif upload_session:
                upload_pks[civ.pk] = upload_session.pk
            civ.save()
            civ_pks_to_add.add(civ.pk)
        elif interface.kind in InterfaceKind.interface_type_file():
            civ = ComponentInterfaceValue.objects.create(interface=interface)
            user_upload.copy_object(to_field=civ.file)
            civ.full_clean()
            civ.save()
            user_upload.delete()
            civ_pks_to_add.add(civ.pk)
        else:
            civ = interface.create_instance(value=value)
            civ_pks_to_add.add(civ.pk)

    return civ_pks_to_add, civ_pks_to_remove, upload_pks


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-micro-short"])
def start_archive_item_update_tasks(
    archive_item_pk, civ_pks_to_add, civ_pks_to_remove, upload_pks
):
    tasks = update_archive_item_values.signature(
        kwargs={
            "archive_item_pk": archive_item_pk,
            "civ_pks_to_add": civ_pks_to_add,
            "civ_pks_to_remove": civ_pks_to_remove,
        },
        immutable=True,
    )

    if len(upload_pks) > 0:
        image_tasks = group(
            chain(
                build_images.signature(
                    kwargs={"upload_session_pk": upload_pk}
                ),
                add_images_to_component_interface_value.signature(
                    kwargs={
                        "component_interface_value_pk": civ_pk,
                        "upload_session_pk": upload_pk,
                    },
                    immutable=True,
                ),
            )
            for civ_pk, upload_pk in upload_pks.items()
        )
        tasks = group(image_tasks, tasks)

    with transaction.atomic():
        on_commit(tasks.apply_async)
