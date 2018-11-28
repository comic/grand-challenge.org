import pytest

from grandchallenge.subdomains.middleware import subdomain_middleware


@pytest.mark.django_db
@pytest.mark.parametrize(
    "host,expected", [["example.com", None], ["test.example.com", "test"]]
)
def test_subdomain_attribute(settings, rf, host, expected):
    # example.com is set in the sites framework
    settings.ALLOWED_HOSTS = [".example.com"]

    request = subdomain_middleware(lambda x: x)(rf.get("/", HTTP_HOST=host))

    assert request.subdomain == expected
