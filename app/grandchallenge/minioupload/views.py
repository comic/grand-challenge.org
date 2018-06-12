# -*- coding: utf-8 -*-
import datetime
import hashlib
import hmac

from django.conf import settings
from django.http import HttpResponse
from django.views.generic import TemplateView
from minio.signer import generate_signing_key


def get_bucket_name():
    return settings.MINIO_DEFAULT_BUCKET_NAME


def presign_string(request):
    # TODO: CSRF protection
    to_sign = request.GET['to_sign']
    date = request.GET['datetime']
    canonical_request = request.GET['canonical_request']

    current_canonical_signature = hashlib.sha256(
        canonical_request.encode('utf-8')
    ).hexdigest()

    # TODO:
    # - ensure that signature is in the string to sign
    # - ensure that the request contains the correct bucket, path and filename
    # - ensure that the timeout of the request is reasonable
    # Use X-Amz-Expires

    signing_key = generate_signing_key(
        datetime.datetime.strptime(date, '%Y%m%dT%H%M%SZ'),
        settings.MINIO_REGION,
        settings.MINIO_SECRET_KEY,
    )

    signature = hmac.new(
        signing_key, to_sign.encode('utf-8'), hashlib.sha256
    ).hexdigest()

    return HttpResponse(signature, content_type='text/HTML')


class EvaporateFileUpload(TemplateView):
    template_name = 'evaporate.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update(
            {
                'MINIO_ACCESS_KEY': settings.MINIO_ACCESS_KEY,
                'MINIO_BUCKET_NAME': get_bucket_name(),
                'MINIO_PUBLIC_URL': settings.MINIO_PUBLIC_URL,
                'MINIO_REGION': settings.MINIO_REGION,
            }
        )

        return context
