from celery import shared_task
from django.db.transaction import on_commit
from guardian.shortcuts import assign_perm

from grandchallenge.algorithms.tasks import create_algorithm_jobs_for_archive
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

    civs = []
    for image in images:
        civ = ComponentInterfaceValue.objects.create(
            interface=interface, image=image
        )
        civs.append(civ)
        item = ArchiveItem.objects.create(archive=archive)
        item.values.set([civ])

    assign_perm("view_image", archive.editors_group, images)
    assign_perm("view_image", archive.uploaders_group, images)
    assign_perm("view_image", archive.users_group, images)

    on_commit(
        lambda: create_algorithm_jobs_for_archive.apply_async(
            kwargs={"archive_pks": list([archive.pk]), "civ_pks": civs},
        )
    )
