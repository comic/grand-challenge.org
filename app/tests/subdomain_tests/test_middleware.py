import pytest
from django.contrib.sites.middleware import CurrentSiteMiddleware

from grandchallenge.subdomains.middleware import (
    challenge_subdomain_middleware,
    subdomain_middleware,
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
    "subdomain",
    [
        None,
        "challengesubdomaintest",
        "ChallengeSubdomainTest",
        "notachallenge",
    ],
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
    else:
        assert request.url == f"http://{SITE_DOMAIN}/"
