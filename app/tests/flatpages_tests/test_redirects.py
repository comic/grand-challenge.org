import pytest
from django.contrib.sites.models import Site

from tests.flatpages_tests.factories import FlatPageFactory, RedirectFactory


@pytest.mark.django_db
def test_redirect_for_flatpage(client):
    old_path = "/test-flatpage/"
    new_path = "/new/url/"
    site = Site.objects.get()

    f = FlatPageFactory(url=old_path)
    f.sites.add(site)

    response = client.get(path=old_path)
    assert response.status_code == 200

    f.url = new_path
    f.save()

    response = client.get(path=old_path)
    assert response.status_code == 404

    RedirectFactory(old_path=old_path, new_path=new_path, site=site)

    response = client.get(path=old_path, follow=True)
    assert response.status_code == 200


@pytest.mark.django_db
def test_trailing_slash_redirects(client):
    path = "/test-flatpage/"
    site = Site.objects.get()

    f = FlatPageFactory(url=path)
    f.sites.add(site)

    response = client.get(path=path[:-1], follow=True)
    assert response.status_code == 200
