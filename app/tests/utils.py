from urllib.parse import urlparse

from django.conf import settings
from django.test import RequestFactory
from django.views.generic import View

from comicmodels.models import ComicSite


def assert_redirect(uri: str, *args):
    request, response = assert_status(302, *args)
    redirect_url = list(urlparse(response.url))[2]
    assert uri == redirect_url
    return request, response


def assert_status(code: int,
                  user: settings.AUTH_USER_MODEL,
                  view: View,
                  challenge: ComicSite,
                  rf: RequestFactory):
    request = rf.get('/rand')
    request.projectname = challenge.short_name

    if user is not None:
        request.user = user

    view = view.as_view()
    response = view(request)

    assert response.status_code == code
    return request, response