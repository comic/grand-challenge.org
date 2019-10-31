from datetime import timedelta

import pytest
from django.conf import settings
from django.contrib.auth.models import Group

from grandchallenge.workstations.models import Session
from tests.factories import SessionFactory, UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_workstation_creators_group_exists():
    assert Group.objects.get(name=settings.WORKSTATIONS_CREATORS_GROUP_NAME)


@pytest.mark.django_db
def test_create_view_permission(client):
    u = UserFactory()
    g = Group.objects.get(name=settings.WORKSTATIONS_CREATORS_GROUP_NAME)

    response = get_view_for_user(
        client=client, user=u, viewname="workstations:create"
    )
    assert response.status_code == 403

    g.user_set.add(u)

    response = get_view_for_user(
        client=client, user=u, viewname="workstations:create"
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_user_autocomplete_permissions(client, two_workstation_sets):
    tests = (
        (two_workstation_sets.ws1.editor, 200),
        (two_workstation_sets.ws1.user, 403),
        (two_workstation_sets.ws2.editor, 200),
        (two_workstation_sets.ws2.user, 403),
        (UserFactory(), 403),
        (UserFactory(is_staff=True), 403),
        (None, 302),
    )

    for test in tests:
        response = get_view_for_user(
            viewname="workstations:users-autocomplete",
            client=client,
            user=test[0],
        )
        assert response.status_code == test[1]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "viewname",
    [
        "workstations:update",
        "workstations:image-create",
        "workstations:image-detail",
        "workstations:image-update",
        "workstations:editors-update",
        "workstations:users-update",
    ],
)
def test_workstation_editor_permissions(
    client, two_workstation_sets, viewname
):
    tests = (
        (two_workstation_sets.ws1.editor, 200),
        (two_workstation_sets.ws1.user, 403),
        (two_workstation_sets.ws2.editor, 403),
        (two_workstation_sets.ws2.user, 403),
        (UserFactory(), 403),
        (UserFactory(is_staff=True), 403),
        (None, 302),
    )

    kwargs = {"slug": two_workstation_sets.ws1.workstation.slug}

    if viewname in ["workstations:image-detail", "workstations:image-update"]:
        kwargs.update({"pk": two_workstation_sets.ws1.image.pk})

    for test in tests:
        response = get_view_for_user(
            viewname=viewname,
            client=client,
            user=test[0],
            reverse_kwargs=kwargs,
        )
        assert response.status_code == test[1]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "viewname",
    [
        "workstations:detail",
        "workstations:session-create",
        "workstations:session-detail",
        "workstations:session-update",
    ],
)
def test_workstation_user_permissions(client, two_workstation_sets, viewname):
    tests = (
        (two_workstation_sets.ws1.editor, 200),
        (two_workstation_sets.ws1.user, 200),
        (two_workstation_sets.ws2.editor, 403),
        (two_workstation_sets.ws2.user, 403),
        (UserFactory(), 403),
        (UserFactory(is_staff=True), 403),
        (None, 302),
    )

    kwargs = {"slug": two_workstation_sets.ws1.workstation.slug}

    if viewname in [
        "workstations:session-detail",
        "workstations:session-update",
    ]:
        s = SessionFactory(
            workstation_image=two_workstation_sets.ws1.image,
            creator=two_workstation_sets.ws1.user,
        )
        kwargs.update({"pk": s.pk})
        tests += ((two_workstation_sets.ws1.user1, 403),)

    for test in tests:
        response = get_view_for_user(
            viewname=viewname,
            client=client,
            user=test[0],
            reverse_kwargs=kwargs,
        )
        assert response.status_code == test[1]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "viewname",
    [
        "workstations:default-session-redirect",
        "workstations:workstation-session-redirect",
        "workstations:workstation-image-session-redirect",
    ],
)
def test_workstation_redirect_permissions(
    client, two_workstation_sets, viewname
):
    two_workstation_sets.ws1.workstation.slug = (
        settings.DEFAULT_WORKSTATION_SLUG
    )
    two_workstation_sets.ws1.workstation.save()

    two_workstation_sets.ws1.image.ready = True
    two_workstation_sets.ws1.image.save()

    tests = (
        (two_workstation_sets.ws1.editor, 302),
        (two_workstation_sets.ws1.user, 302),
        (two_workstation_sets.ws2.editor, 403),
        (two_workstation_sets.ws2.user, 403),
        (UserFactory(), 403),
        (UserFactory(is_staff=True), 403),
        (None, 302),
    )

    kwargs = {}

    if viewname in [
        "workstations:workstation-session-redirect",
        "workstations:workstation-image-session-redirect",
    ]:
        kwargs.update({"slug": two_workstation_sets.ws1.workstation.slug})

    if viewname == "workstations:workstation-image-session-redirect":
        kwargs.update({"pk": two_workstation_sets.ws1.image.pk})

    for test in tests:
        response = get_view_for_user(
            viewname=viewname,
            client=client,
            user=test[0],
            reverse_kwargs=kwargs,
        )
        assert response.status_code == test[1]

        if test[1] == 302 and test[0] is not None:
            session = Session.objects.get(creator=test[0])
            assert response.url == session.get_absolute_url()


@pytest.mark.django_db
def test_session_proxy_permissions(client, two_workstation_sets):
    tests = (
        (two_workstation_sets.ws1.editor, 403),
        (two_workstation_sets.ws1.user, 200),
        (two_workstation_sets.ws1.user1, 403),
        (two_workstation_sets.ws2.editor, 403),
        (two_workstation_sets.ws2.user, 403),
        (UserFactory(), 403),
        (UserFactory(is_staff=True), 403),
        (None, 403),
    )

    s = SessionFactory(
        workstation_image=two_workstation_sets.ws1.image,
        creator=two_workstation_sets.ws1.user,
    )

    for test in tests:
        response = get_view_for_user(
            viewname="workstations:session-proxy",
            client=client,
            user=test[0],
            reverse_kwargs={
                "slug": s.workstation_image.workstation.slug,
                "pk": s.pk,
                "path": "foo/bar/../../baz",
            },
        )
        assert response.status_code == test[1]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "viewname", ["api:session-detail", "api:session-list"]
)
def test_session_api_permissions(client, two_workstation_sets, viewname):
    tests = (
        (two_workstation_sets.ws1.editor, 200),
        (two_workstation_sets.ws1.user, 200),
        (two_workstation_sets.ws1.user1, 404),
        (two_workstation_sets.ws2.editor, 404),
        (two_workstation_sets.ws2.user, 404),
        (UserFactory(), 404),
        (UserFactory(is_staff=True), 404),
        (None, 401),
    )

    s = SessionFactory(
        workstation_image=two_workstation_sets.ws1.image,
        creator=two_workstation_sets.ws1.user,
    )

    if viewname == "api:session-detail":
        kwargs = {"pk": s.pk}
    else:
        kwargs = {}

    for test in tests:
        response = get_view_for_user(
            viewname=viewname,
            client=client,
            user=test[0],
            reverse_kwargs=kwargs,
        )
        if viewname == "api:session-list" and test[0] is not None:
            if test[1] == 200:
                assert response.json()["count"] == 1
            else:
                assert response.json()["count"] == 0
        else:
            assert response.status_code == test[1]


@pytest.mark.django_db
def test_session_api_patch_permissions(client, two_workstation_sets):
    tests = (
        (two_workstation_sets.ws1.editor, 200, True),
        (two_workstation_sets.ws1.user, 200, True),
        (two_workstation_sets.ws1.user1, 404, False),
        (two_workstation_sets.ws2.editor, 404, False),
        (two_workstation_sets.ws2.user, 404, False),
        (UserFactory(), 404, False),
        (UserFactory(is_staff=True), 404, False),
        (None, 401, False),
    )

    for test in tests:
        s = SessionFactory(
            workstation_image=two_workstation_sets.ws1.image,
            creator=two_workstation_sets.ws1.user,
        )

        response = get_view_for_user(
            viewname="api:session-keep-alive",
            client=client,
            method=client.patch,
            user=test[0],
            reverse_kwargs={"pk": s.pk},
            content_type="application/json",
        )
        assert response.status_code == test[1]

        # The maximum duration should have changed from the default
        s.refresh_from_db()
        assert s.status == s.QUEUED  # Read only, always unchanged
        assert (s.maximum_duration == timedelta(minutes=10)) is not test[2]
