import logging
import traceback

from raven.contrib.django.models import client
from rest_framework.response import Response

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    from rest_framework.views import exception_handler
    response = exception_handler(exc, context)

    # If error is not handled already by DRF (handles user errors (validation etc.))
    if response is None:
        logger.exception("DRF exception")
        response = Response({'error': str(exc), 'stack': traceback.format_exc().splitlines()}, 500)
        try:
            client.captureException()
        except:
            pass

    return response
