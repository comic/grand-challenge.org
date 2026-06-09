import pytest

from grandchallenge.broken_links.models import BrokenLink, IgnoredPattern


@pytest.mark.django_db
def test_creating_ignored_pattern_deletes_matching_broken_links():
    BrokenLink.objects.create(
        domain="testserver",
        path="/ignored/page",
        referer="http://testserver/ref/",
        user_agent="Mozilla/5.0",
        ip_address="127.0.0.1",
        is_internal=True,
    )
    BrokenLink.objects.create(
        domain="testserver",
        path="/keep/page",
        referer="http://testserver/ref/",
        user_agent="Mozilla/5.0",
        ip_address="127.0.0.1",
        is_internal=True,
    )

    IgnoredPattern.objects.create(pattern=r"^/ignored/.*")

    assert BrokenLink.objects.count() == 1
    assert BrokenLink.objects.get().path == "/keep/page"
