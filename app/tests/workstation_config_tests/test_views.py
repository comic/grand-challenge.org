import pytest
from django.contrib.auth.models import Permission
from django.core.exceptions import ObjectDoesNotExist

from grandchallenge.workstation_configs.models import WorkstationConfig
from tests.factories import UserFactory, WorkstationConfigFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_workstation_config_list_view(client):
    wc1, wc2 = WorkstationConfigFactory(), WorkstationConfigFactory()
    user = UserFactory()
    response = get_view_for_user(
        viewname="workstation-configs:list", client=client, user=user
    )

    assert response.status_code == 200
    assert wc1.get_absolute_url() in response.rendered_content
    assert wc2.get_absolute_url() in response.rendered_content


@pytest.mark.django_db
def test_workstation_config_detail_view(client):
    wc = WorkstationConfigFactory()
    user = UserFactory()
    response = get_view_for_user(
        viewname="workstation-configs:detail",
        reverse_kwargs={"slug": wc.slug},
        client=client,
        user=user,
    )

    assert response.status_code == 200
    assert wc.title in response.rendered_content


@pytest.mark.django_db
def test_workstation_config_create_view(client):
    user = UserFactory()
    response = get_view_for_user(
        viewname="workstation-configs:create", client=client, user=user
    )
    assert response.status_code == 403

    permission = Permission.objects.get(codename="add_workstationconfig")
    user.user_permissions.add(permission)
    response = get_view_for_user(
        viewname="workstation-configs:create", client=client, user=user
    )
    assert response.status_code == 200

    assert WorkstationConfig.objects.count() == 0
    response = get_view_for_user(
        viewname="workstation-configs:create",
        client=client,
        user=user,
        method=client.post,
        data={"title": "foo"},
    )
    assert WorkstationConfig.objects.count() == 1
    assert WorkstationConfig.objects.get(title="foo").creator == user


@pytest.mark.django_db
def test_workstation_config_update_view(client):
    wc = WorkstationConfigFactory(title="foo")
    user = UserFactory()
    response = get_view_for_user(
        viewname="workstation-configs:update",
        reverse_kwargs={"slug": wc.slug},
        client=client,
        user=user,
    )
    assert response.status_code == 403

    wc.creator = user
    wc.save()
    response = get_view_for_user(
        viewname="workstation-configs:update",
        reverse_kwargs={"slug": wc.slug},
        client=client,
        user=user,
    )
    assert response.status_code == 200

    assert wc.title == "foo"
    response = get_view_for_user(
        viewname="workstation-configs:update",
        reverse_kwargs={"slug": wc.slug},
        client=client,
        user=user,
        method=client.post,
        data={"title": "bar"},
    )
    wc.refresh_from_db()
    assert wc.title == "bar"


@pytest.mark.django_db
def test_workstation_config_delete_view(client):
    wc = WorkstationConfigFactory(title="foo")
    user = UserFactory()
    response = get_view_for_user(
        viewname="workstation-configs:delete",
        reverse_kwargs={"slug": wc.slug},
        client=client,
        user=user,
    )
    assert response.status_code == 403

    wc.creator = user
    wc.save()
    response = get_view_for_user(
        viewname="workstation-configs:delete",
        reverse_kwargs={"slug": wc.slug},
        client=client,
        user=user,
        follow=True,
    )
    assert response.status_code == 200
    assert (
        f'Are you sure that you want to delete workstation config "{wc.title}"?'
        in response.rendered_content
    )

    response = get_view_for_user(
        viewname="workstation-configs:delete",
        reverse_kwargs={"slug": wc.slug},
        client=client,
        user=user,
        method=client.post,
    )
    with pytest.raises(ObjectDoesNotExist):
        wc.refresh_from_db()
