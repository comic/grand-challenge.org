from datetime import timedelta

import pytest
from django.utils import timezone

from grandchallenge.broken_links.models import (
    MAX_BROKEN_LINK_AGE_DAYS,
    BrokenLink,
)
from grandchallenge.broken_links.tasks import delete_old_broken_links


@pytest.mark.django_db
def test_delete_old_broken_links():
    old = BrokenLink.objects.create(
        domain="testserver",
        path="/old/",
        referer="http://testserver/ref/",
        user_agent="Mozilla/5.0",
        ip_address="127.0.0.1",
        is_internal=True,
    )
    BrokenLink.objects.filter(pk=old.pk).update(
        created=timezone.now() - timedelta(days=MAX_BROKEN_LINK_AGE_DAYS + 1)
    )

    recent = BrokenLink.objects.create(
        domain="testserver",
        path="/recent/",
        referer="http://testserver/ref/",
        user_agent="Mozilla/5.0",
        ip_address="127.0.0.1",
        is_internal=True,
    )

    delete_old_broken_links()

    assert BrokenLink.objects.count() == 1
    assert BrokenLink.objects.get().pk == recent.pk
