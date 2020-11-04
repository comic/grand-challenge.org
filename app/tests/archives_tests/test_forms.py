import pytest
from django.contrib.auth.models import Permission

from grandchallenge.archives.models import (
    Archive,
    ArchivePermissionRequest,
)
from grandchallenge.core.management.commands.init_gc_demo import (
    get_temporary_image,
)
from tests.archives_tests.factories import (
    ArchiveFactory,
    ArchivePermissionRequestFactory,
)
from tests.factories import UserFactory, WorkstationFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_editor_update_form(client):
    archive = ArchiveFactory()

    editor = UserFactory()
    archive.editors_group.user_set.add(editor)

    assert archive.editors_group.user_set.count() == 1

    new_editor = UserFactory()
    assert not archive.is_editor(user=new_editor)
    response = get_view_for_user(
        viewname="archives:editors-update",
        client=client,
        method=client.post,
        data={"user": new_editor.pk, "action": "ADD"},
        reverse_kwargs={"slug": archive.slug},
        follow=True,
        user=editor,
    )
    assert response.status_code == 200

    archive.refresh_from_db()
    assert archive.editors_group.user_set.count() == 2
    assert archive.is_editor(user=new_editor)

    response = get_view_for_user(
        viewname="archives:editors-update",
        client=client,
        method=client.post,
        data={"user": new_editor.pk, "action": "REMOVE"},
        reverse_kwargs={"slug": archive.slug},
        follow=True,
        user=editor,
    )
    assert response.status_code == 200

    archive.refresh_from_db()
    assert archive.editors_group.user_set.count() == 1
    assert not archive.is_editor(user=new_editor)


@pytest.mark.django_db
def test_user_update_form(client):
    archive = ArchiveFactory()

    editor = UserFactory()
    archive.editors_group.user_set.add(editor)

    assert archive.users_group.user_set.count() == 0

    new_user = UserFactory()
    pr = ArchivePermissionRequestFactory(user=new_user, archive=archive)

    assert not archive.is_user(user=new_user)
    assert pr.status == ArchivePermissionRequest.PENDING
    response = get_view_for_user(
        viewname="archives:users-update",
        client=client,
        method=client.post,
        data={"user": new_user.pk, "action": "ADD"},
        reverse_kwargs={"slug": archive.slug},
        follow=True,
        user=editor,
    )
    assert response.status_code == 200

    archive.refresh_from_db()
    pr.refresh_from_db()
    assert archive.users_group.user_set.count() == 1
    assert archive.is_user(user=new_user)
    assert pr.status == ArchivePermissionRequest.ACCEPTED

    response = get_view_for_user(
        viewname="archives:users-update",
        client=client,
        method=client.post,
        data={"user": new_user.pk, "action": "REMOVE"},
        reverse_kwargs={"slug": archive.slug},
        follow=True,
        user=editor,
    )
    assert response.status_code == 200

    archive.refresh_from_db()
    pr.refresh_from_db()
    assert archive.users_group.user_set.count() == 0
    assert not archive.is_user(user=new_user)
    assert pr.status == ArchivePermissionRequest.REJECTED


@pytest.mark.django_db
def test_archive_create(client):
    # The archive creator should automatically get added to the editors group
    creator = UserFactory()
    add_archive_perm = Permission.objects.get(
        codename=f"add_{Archive._meta.model_name}"
    )
    creator.user_permissions.add(add_archive_perm)

    ws = WorkstationFactory()

    def try_create_archive():
        return get_view_for_user(
            viewname="archives:create",
            client=client,
            method=client.post,
            data={
                "title": "foo bar",
                "logo": get_temporary_image(),
                "workstation": ws.pk,
            },
            follow=True,
            user=creator,
        )

    response = try_create_archive()
    assert "error_1_id_workstation" in response.rendered_content

    # The editor must have view permissions for the workstation to add it
    ws.add_user(user=creator)

    response = try_create_archive()
    assert "error_1_id_workstation" not in response.rendered_content
    assert response.status_code == 200

    archive = Archive.objects.get(title="foo bar")

    assert archive.slug == "foo-bar"
    assert archive.is_editor(user=creator)
    assert not archive.is_user(user=creator)
