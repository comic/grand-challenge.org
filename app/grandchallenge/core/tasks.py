import json
import tarfile
import uuid

from celery import shared_task
from django.apps import apps
from django.core.exceptions import ValidationError
from django.core.management import call_command


@shared_task
def clear_sessions():
    """ Clear the expired sessions stored in django_session """
    call_command('clearsessions')


@shared_task()
def validate_docker_image_async(
        *, pk: uuid.UUID, app_label: str, object_name: str
):
    model = apps.get_model(app_label=app_label, model_name=object_name)

    instance = model.objects.get(pk=pk)
    instance.image.open(mode='rb')

    try:
        with tarfile.open(fileobj=instance.image, mode='r') as t:
            member = dict(zip(t.getnames(), t.getmembers()))['manifest.json']
            manifest = t.extractfile(member).read()
    except (KeyError, tarfile.ReadError) as e:
        model.objects.filter(pk=pk).update(status=(
            'manifest.json not found at the root of the container image file. '
            'Was this created with docker save?'
        ))
        raise ValidationError("Invalid Dockerfile")

    manifest = json.loads(manifest)

    if len(manifest) != 1:
        model.objects.filter(pk=pk).update(status=(
            f'The container image file should only have 1 image. '
            f'This file contains {len(manifest)}.'
        ))
        raise ValidationError("Invalid Dockerfile")

    model.objects.filter(pk=pk).update(
        image_sha256=f"sha256:{manifest[0]['Config'][:64]}", ready=True
    )
