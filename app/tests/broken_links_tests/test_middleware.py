import pytest
from django.test import RequestFactory

from grandchallenge.broken_links.middleware import BrokenLinkMiddleware
from grandchallenge.broken_links.models import BrokenLink, IgnoredPattern


@pytest.mark.django_db
class TestBrokenLinkMiddleware:
    def test_404_response_creates_broken_link(self, settings):
        settings.DEBUG = False
        settings.ALLAUTH_TRUSTED_PROXY_COUNT = 3
        factory = RequestFactory()
        request = factory.get("/missing-page/")
        request.META["HTTP_REFERER"] = "http://testserver/some-page/"
        request.META["HTTP_X_FORWARDED_FOR"] = (
            "203.0.113.1, 10.0.0.1, 10.0.0.2"
        )

        middleware = BrokenLinkMiddleware(get_response=lambda r: None)

        from django.http import HttpResponseNotFound

        response = HttpResponseNotFound()

        middleware.process_response(request=request, response=response)

        assert BrokenLink.objects.count() == 1
        broken_link = BrokenLink.objects.get()
        assert broken_link.path == "/missing-page/"
        assert broken_link.referer == "http://testserver/some-page/"
        assert broken_link.domain == "testserver"
        assert broken_link.ip_address == "203.0.113.1"

    def test_non_404_response_does_not_create_broken_link(self, settings):
        settings.DEBUG = False
        factory = RequestFactory()
        request = factory.get("/existing-page/")
        request.META["HTTP_REFERER"] = "http://testserver/some-page/"

        middleware = BrokenLinkMiddleware(get_response=lambda r: None)

        from django.http import HttpResponse

        response = HttpResponse()

        middleware.process_response(request=request, response=response)

        assert BrokenLink.objects.count() == 0

    def test_debug_mode_does_not_create_broken_link(self, settings):
        settings.DEBUG = True
        factory = RequestFactory()
        request = factory.get("/missing-page/")
        request.META["HTTP_REFERER"] = "http://testserver/some-page/"

        middleware = BrokenLinkMiddleware(get_response=lambda r: None)

        from django.http import HttpResponseNotFound

        response = HttpResponseNotFound()

        middleware.process_response(request=request, response=response)

        assert BrokenLink.objects.count() == 0

    def test_ignorable_request_does_not_create_broken_link(self, settings):
        settings.DEBUG = False
        factory = RequestFactory()
        request = factory.get("/missing-page/")
        request.META.pop("HTTP_REFERER", None)

        middleware = BrokenLinkMiddleware(get_response=lambda r: None)

        from django.http import HttpResponseNotFound

        response = HttpResponseNotFound()

        middleware.process_response(request=request, response=response)

        assert BrokenLink.objects.count() == 0

    def test_database_ignored_pattern_suppresses_broken_link(self, settings):
        settings.DEBUG = False
        IgnoredPattern.objects.create(pattern=r"^/ignored/.*$")

        factory = RequestFactory()
        request = factory.get("/ignored/something")
        request.META["HTTP_REFERER"] = "http://testserver/page/"

        middleware = BrokenLinkMiddleware(get_response=lambda r: None)

        from django.http import HttpResponseNotFound

        response = HttpResponseNotFound()

        middleware.process_response(request=request, response=response)

        assert BrokenLink.objects.count() == 0

    def test_database_ignored_pattern_does_not_suppress_non_matching(
        self, settings
    ):
        settings.DEBUG = False
        IgnoredPattern.objects.create(pattern=r"^/ignored/.*$")

        factory = RequestFactory()
        request = factory.get("/not-ignored/page")
        request.META["HTTP_REFERER"] = "http://testserver/page/"

        middleware = BrokenLinkMiddleware(get_response=lambda r: None)

        from django.http import HttpResponseNotFound

        response = HttpResponseNotFound()

        middleware.process_response(request=request, response=response)

        assert BrokenLink.objects.count() == 1
