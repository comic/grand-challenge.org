import pytest
from actstream.actions import is_following
from django.contrib.auth.models import Permission
from django_capture_on_commit_callbacks import capture_on_commit_callbacks

from grandchallenge.algorithms.models import Job
from grandchallenge.archives.models import (
    Archive,
    ArchivePermissionRequest,
)
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
    InterfaceKind,
)
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
)
from tests.archives_tests.factories import (
    ArchiveFactory,
    ArchiveItemFactory,
    ArchivePermissionRequestFactory,
)
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
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
def test_archive_create(client, uploaded_image):
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
                "logo": uploaded_image(),
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
    assert is_following(user=creator, obj=archive)


@pytest.mark.django_db
def test_social_image_meta_tag(client, uploaded_image):
    creator = UserFactory()
    add_archive_perm = Permission.objects.get(
        codename=f"add_{Archive._meta.model_name}"
    )
    creator.user_permissions.add(add_archive_perm)

    ws = WorkstationFactory()
    ws.add_user(user=creator)

    def create_archive():
        return get_view_for_user(
            viewname="archives:create",
            client=client,
            method=client.post,
            data={
                "title": "foo bar",
                "logo": uploaded_image(),
                "social_image": uploaded_image(),
                "workstation": ws.pk,
            },
            follow=True,
            user=creator,
        )

    response = create_archive()
    assert response.status_code == 200

    archive = Archive.objects.get(title="foo bar")
    assert str(archive.social_image.x20.url) in response.content.decode()


@pytest.mark.django_db
def test_archive_item_form(client, settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    archive = ArchiveFactory()

    editor = UserFactory()
    archive.editors_group.user_set.add(editor)

    ci = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.BOOL
    )
    civ = ComponentInterfaceValueFactory(
        interface=ci, value=True, file=None, image=None
    )
    ai = ArchiveItemFactory(archive=archive)
    ai.values.add(civ)

    response = get_view_for_user(
        viewname="archives:item-edit",
        client=client,
        method=client.get,
        reverse_kwargs={"slug": archive.slug, "id": ai.pk},
        follow=True,
        user=editor,
    )
    assert response.status_code == 200

    for _ci in ComponentInterface.objects.all():
        assert _ci.slug in response.rendered_content

    assert f'id="id_{ci.slug}" checked' in response.rendered_content

    assert Job.objects.count() == 0

    alg = AlgorithmFactory()
    AlgorithmImageFactory(algorithm=alg, ready=True)
    alg.inputs.set([ci])
    with capture_on_commit_callbacks(execute=True):
        archive.algorithms.add(alg)

    assert Job.objects.count() == 1

    civ_count = ComponentInterfaceValue.objects.count()

    with capture_on_commit_callbacks(execute=True):
        with capture_on_commit_callbacks(execute=True):
            response = get_view_for_user(
                viewname="archives:item-edit",
                client=client,
                method=client.post,
                reverse_kwargs={"slug": archive.slug, "id": ai.pk},
                data={ci.slug: False},
                follow=True,
                user=editor,
            )

    assert ai.values.filter(pk=civ.pk).count() == 0
    # This should created a new CIV as they are immutable
    assert ComponentInterfaceValue.objects.count() == civ_count + 1

    # A new job should have been created, because the value for 'bool'
    # has changed
    assert Job.objects.count() == 2

    with capture_on_commit_callbacks(execute=True):
        with capture_on_commit_callbacks(execute=True):
            response = get_view_for_user(
                viewname="archives:item-edit",
                client=client,
                method=client.post,
                reverse_kwargs={"slug": archive.slug, "id": ai.pk},
                data={ci.slug: True},
                follow=True,
                user=editor,
            )

    # New jobs should be created as there is a new CIV
    assert Job.objects.count() == 3
    assert ComponentInterfaceValue.objects.count() == civ_count + 2
