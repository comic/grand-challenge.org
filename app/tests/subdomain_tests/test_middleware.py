import pytest
from django.contrib.sites.middleware import CurrentSiteMiddleware
from django.core.handlers.wsgi import WSGIRequest

from grandchallenge.subdomains.middleware import (
    challenge_subdomain_middleware,
    subdomain_middleware,
    subdomain_urlconf_middleware,
)
from tests.factories import ChallengeFactory

# The domain that is set for the main site, set by RequestFactory
SITE_DOMAIN = "testserver"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "host,subdomain",
    [
        [SITE_DOMAIN, None],
        [f"test.{SITE_DOMAIN}", "test"],
        [f"TEST.{SITE_DOMAIN}", "test"],
        [f"www.test.{SITE_DOMAIN}", "www.test"],
        [f"www.{SITE_DOMAIN}", "www"],
    ],
)
def test_subdomain_attribute(settings, rf, host, subdomain):
    settings.ALLOWED_HOSTS = [f".{SITE_DOMAIN}"]
    request = CurrentSiteMiddleware(lambda x: x)(rf.get("/", HTTP_HOST=host))
    request = subdomain_middleware(lambda x: x)(request)
    assert request.subdomain == subdomain


@pytest.mark.django_db
@pytest.mark.parametrize(
    "host,subdomain",
    [
        [f"{SITE_DOMAIN}", None],
        [f"test.{SITE_DOMAIN}", "test"],
        [f"not{SITE_DOMAIN}", None],
        [f"www.not{SITE_DOMAIN}", None],
    ],
)
def test_invalid_domain(settings, rf, host, subdomain):
    # Other domains will get the main challenge by setting subdomain = None
    settings.ALLOWED_HOSTS = [f".{SITE_DOMAIN}", f".not{SITE_DOMAIN}"]
    request = CurrentSiteMiddleware(lambda x: x)(rf.get("/", HTTP_HOST=host))
    request = subdomain_middleware(lambda x: x)(request)
    assert request.subdomain == subdomain


@pytest.mark.django_db
@pytest.mark.parametrize(
    "subdomain", [None, "challengesubdomaintest", "ChallengeSubdomainTest"]
)
def test_challenge_attribute(settings, rf, subdomain):
    settings.ALLOWED_HOSTS = [f".{SITE_DOMAIN}"]

    c = ChallengeFactory(short_name="challengesubdomaintest")

    request = rf.get("/")
    request.subdomain = subdomain

    assert not hasattr(request, "challenge")

    request = CurrentSiteMiddleware(lambda x: x)(request)
    request = challenge_subdomain_middleware(lambda x: x)(request)

    if subdomain is None:
        assert request.challenge is None
    elif subdomain.lower() == c.short_name.lower():
        assert request.challenge == c


@pytest.mark.django_db
@pytest.mark.parametrize(
    "subdomain,response_type,expected_challenge",
    [
        (None, WSGIRequest, False),
        ("us-east-1", WSGIRequest, False),
        ("c", WSGIRequest, True),
    ],
)
def test_rendering_challenge_settings(
    settings, rf, subdomain, response_type, expected_challenge
):
    """Requests on rendering subdomains should not have a challenge attached nor redirect."""
    settings.ALLOWED_HOSTS = [f".{SITE_DOMAIN}"]
    c = ChallengeFactory(short_name="c")

    request = rf.get("/")
    request.subdomain = subdomain

    assert not hasattr(request, "challenge")

    request = CurrentSiteMiddleware(lambda x: x)(request)
    request = challenge_subdomain_middleware(lambda x: x)(request)

    assert isinstance(request, response_type)

    if response_type is WSGIRequest:
        if expected_challenge:
            assert request.challenge == c
        else:
            assert request.challenge is None


@pytest.mark.django_db
@pytest.mark.parametrize(
    "subdomain,expected_subdomain,expected_challenge,expected_url_conf",
    [
        (None, None, False, "tests.urls.root"),
        ("c", "c", True, "config.urls.challenge_subdomain"),
        ("C", "c", True, "config.urls.challenge_subdomain"),
        ("us-east-1", "us-east-1", False, "config.urls.rendering_subdomain"),
    ],
)
def test_url_conf_set(
    settings,
    rf,
    subdomain,
    expected_subdomain,
    expected_challenge,
    expected_url_conf,
):
    """Subdomains should have the correct url_conf attached."""
    settings.ALLOWED_HOSTS = [f".{SITE_DOMAIN}"]
    c = ChallengeFactory(short_name="c")

    if subdomain is not None:
        host = f"{subdomain}.{SITE_DOMAIN}"
    else:
        host = SITE_DOMAIN

    request = CurrentSiteMiddleware(lambda x: x)(rf.get("/", HTTP_HOST=host))
    request = subdomain_middleware(lambda x: x)(request)
    request = challenge_subdomain_middleware(lambda x: x)(request)
    request = subdomain_urlconf_middleware(lambda x: x)(request)

    assert request.subdomain == expected_subdomain
    assert request.urlconf == expected_url_conf
    if expected_challenge:
        assert request.challenge == c
    else:
        assert request.challenge is None
