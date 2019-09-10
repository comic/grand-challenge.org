import logging
import traceback

from rest_framework.response import Response

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    from rest_framework.utils.serializer_helpers import ReturnDict
    from rest_framework.exceptions import ErrorDetail, ValidationError
    from rest_framework.views import exception_handler
    response = exception_handler(exc, context)

    # bad request.. probably validationError
    if isinstance(exc, ValidationError) and response.status_code == 400 and isinstance(response.data, ReturnDict):
        for (key, value) in response.data.items():
            response.data[key] = [{
                'message': str(error),
                'code': error.code
            } for error in value]

    # If error is not handled already by DRF (handles user errors (validation etc.))
    if response is None:
        logger.exception("Non-DRF exception")
        response = Response({'error': str(exc), 'stack': traceback.format_exc().splitlines()}, 500)

    return response
