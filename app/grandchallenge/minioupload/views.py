# -*- coding: utf-8 -*-
from datetime import timedelta

from django.conf import settings
from django.http import HttpResponse
from django.views.generic import TemplateView
from minio import Minio
from minio.error import BucketAlreadyOwnedByYou, BucketAlreadyExists
from minio.signer import presign_v4


def presigned_url(request, filename):
    bucket_name = 'testbucket'
    access_key = settings.MINIO_ACCESS_KEY
    secret_key = settings.MINIO_SECRET_KEY

    minio_client = Minio(
        'minio:9000',  # the minio url as seen by the web container
        access_key=access_key,
        secret_key=secret_key,
        secure=False,
    )

    try:
        minio_client.make_bucket(bucket_name)
    except (BucketAlreadyExists, BucketAlreadyOwnedByYou):
        pass

    # Usually you would use minio_client.presigned_put_object, but the client
    # cannot see this url. So, create this ourselves by using the publically
    # available url.
    url = presign_v4(
        'PUT',
        f'{settings.MINIO_PUBLIC_URL}/{bucket_name}/{filename}',
        access_key=access_key,
        secret_key=secret_key,
        expires=int(timedelta(days=1).total_seconds()),
    )

    return HttpResponse(url)


class MinioFileUpload(TemplateView):
    template_name = 'minio.html'
