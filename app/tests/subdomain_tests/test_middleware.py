import pytest

from grandchallenge.subdomains.middleware import subdomain_middleware


@pytest.mark.django_db
@pytest.mark.parametrize(
    "host,subdomain",
    [
        ["example.com", None],
        ["test.example.com", "test"],
        ["TEST.example.com", "test"],
        ["www.test.example.com", "www.test"],
        ["www.example.com", "www"],
    ],
)
def test_subdomain_attribute(settings, rf, host, subdomain):
    # example.com is set in the sites framework
    settings.ALLOWED_HOSTS = [".example.com"]

    request = subdomain_middleware(lambda x: x)(rf.get("/", HTTP_HOST=host))

    assert request.subdomain == subdomain
