# -*- coding: utf-8 -*-
import datetime
import hashlib
import hmac
from datetime import timedelta

from django.conf import settings
from django.http import HttpResponse
from django.views.generic import TemplateView
from minio import Minio
from minio.error import BucketAlreadyOwnedByYou, BucketAlreadyExists
from minio.signer import presign_v4, generate_signing_key


def get_bucket_name():
    return 'testbucket'


def presigned_url(request, filename):
    bucket_name = get_bucket_name()
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


def presign_string(request):
    # TODO: Try this with a real AWS bucket
    to_sign = request.GET['to_sign']
    date = request.GET['datetime']

    canonical_request = request.GET['canonical_request']
    current_canonical_signature = hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()

    new_canonical_request = canonical_request.replace('host:localhost', 'host:localhost:9000')
    new_canonical_signature = hashlib.sha256(new_canonical_request.encode('utf-8')).hexdigest()

    to_sign = to_sign.replace(current_canonical_signature, new_canonical_signature)


    signing_key = generate_signing_key(datetime.datetime.strptime(date,
                                                                  '%Y%m%dT%H%M%SZ'),
                                       'us-east-1',
                                       settings.MINIO_SECRET_KEY)
    signature = hmac.new(signing_key, to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

    return HttpResponse(signature, content_type='text/HTML')


class MinioFileUpload(TemplateView):
    template_name = 'minio.html'


class EvaporateFileUpload(TemplateView):
    template_name = 'evaporate.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update(
            {
                'MINIO_ACCESS_KEY': settings.MINIO_ACCESS_KEY,
                'MINIO_BUCKET_NAME': get_bucket_name(),
            }
        )

        return context
