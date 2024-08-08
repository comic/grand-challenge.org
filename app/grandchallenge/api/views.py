from django.conf import settings
from django.http import HttpResponse


def lowest_supported_gcapi_version(request):
    return HttpResponse(settings.GCAPI_LOWEST_SUPPORTED_VERSION)
