import pytest

from grandchallenge.broken_links.models import BrokenLink
from tests.factories import UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_dashboard_requires_staff(client):
    user = UserFactory()
    response = get_view_for_user(
        viewname="broken-links:dashboard",
        client=client,
        user=user,
    )
    assert response.status_code == 403

    staff_user = UserFactory(is_staff=True)
    response = get_view_for_user(
        viewname="broken-links:dashboard",
        client=client,
        user=staff_user,
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_dashboard_not_accessible_to_anonymous(client):
    response = get_view_for_user(
        viewname="broken-links:dashboard",
        client=client,
        user=None,
    )
    assert response.status_code == 302


@pytest.mark.django_db
def test_dashboard_shows_summaries(client):
    user = UserFactory(is_staff=True)
    BrokenLink.objects.create(
        domain="testserver",
        path="/missing/",
        referer="http://testserver/page/",
        user_agent="Mozilla/5.0",
        ip_address="127.0.0.1",
        is_internal=True,
    )
    BrokenLink.objects.create(
        domain="testserver",
        path="/missing/",
        referer="http://testserver/other/",
        user_agent="Mozilla/5.0",
        ip_address="127.0.0.1",
        is_internal=True,
    )

    response = get_view_for_user(
        viewname="broken-links:dashboard",
        client=client,
        user=user,
    )
    assert response.status_code == 200
    content = response.rendered_content
    assert "/missing/" in content
    assert "2" in content


@pytest.mark.django_db
def test_dashboard_filters_by_days(client):
    user = UserFactory(is_staff=True)
    BrokenLink.objects.create(
        domain="testserver",
        path="/recent/",
        referer="http://testserver/page/",
        user_agent="Mozilla/5.0",
        ip_address="127.0.0.1",
        is_internal=True,
    )

    response = get_view_for_user(
        viewname="broken-links:dashboard",
        client=client,
        user=user,
        data={"days": "7"},
    )
    assert response.status_code == 200
    assert "/recent/" in response.rendered_content


@pytest.mark.django_db
def test_dashboard_ignores_invalid_days(client):
    user = UserFactory(is_staff=True)

    response = get_view_for_user(
        viewname="broken-links:dashboard",
        client=client,
        user=user,
        data={"days": "999"},
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_dashboard_shows_top_ip_addresses(client):
    user = UserFactory(is_staff=True)
    BrokenLink.objects.create(
        domain="testserver",
        path="/missing/",
        referer="http://testserver/page/",
        user_agent="Mozilla/5.0",
        ip_address="192.168.1.1",
        is_internal=True,
    )
    BrokenLink.objects.create(
        domain="testserver",
        path="/other/",
        referer="http://testserver/page/",
        user_agent="Mozilla/5.0",
        ip_address="192.168.1.1",
        is_internal=True,
    )
    BrokenLink.objects.create(
        domain="testserver",
        path="/another/",
        referer="http://testserver/page/",
        user_agent="Mozilla/5.0",
        ip_address="10.0.0.1",
        is_internal=False,
    )

    response = get_view_for_user(
        viewname="broken-links:dashboard",
        client=client,
        user=user,
    )
    assert response.status_code == 200
    context = response.context
    top_ips = list(context["top_ip_addresses"])
    assert top_ips[0]["ip_address"] == "192.168.1.1"
    assert top_ips[0]["count"] == 2
    assert top_ips[1]["ip_address"] == "10.0.0.1"
    assert top_ips[1]["count"] == 1
