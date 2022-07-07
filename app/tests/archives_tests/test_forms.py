import pytest
from actstream.actions import is_following
from django.contrib.auth.models import Permission
from django_capture_on_commit_callbacks import capture_on_commit_callbacks

from grandchallenge.algorithms.models import Job
from grandchallenge.archives.models import Archive, ArchivePermissionRequest
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
    InterfaceKind,
)
from grandchallenge.core.utils.access_requests import (
    AccessRequestHandlingOptions,
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
from tests.factories import ImageFactory, UserFactory, WorkstationFactory
from tests.reader_studies_tests.factories import ReaderStudyFactory
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
                "access_request_handling": AccessRequestHandlingOptions.MANUAL_REVIEW,
                "view_content": "{}",
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
                "access_request_handling": AccessRequestHandlingOptions.MANUAL_REVIEW,
                "view_content": "{}",
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
    user = UserFactory()

    archive.editors_group.user_set.add(editor)

    ci = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.BOOL
    )
    civ = ComponentInterfaceValueFactory(
        interface=ci, value=True, file=None, image=None
    )
    ai = ArchiveItemFactory(archive=archive)
    ai.values.add(civ)

    # user cannot edit archive item
    response = get_view_for_user(
        viewname="archives:item-edit",
        client=client,
        method=client.get,
        reverse_kwargs={
            "archive_slug": archive.slug,
            "pk": ai.pk,
            "interface_slug": ci.slug,
        },
        follow=True,
        user=user,
    )
    assert response.status_code == 403

    archive.add_uploader(user)
    response = get_view_for_user(
        viewname="archives:item-edit",
        client=client,
        method=client.get,
        reverse_kwargs={
            "archive_slug": archive.slug,
            "pk": ai.pk,
            "interface_slug": ci.slug,
        },
        follow=True,
        user=user,
    )
    assert response.status_code == 200

    response = get_view_for_user(
        viewname="archives:item-edit",
        client=client,
        method=client.get,
        reverse_kwargs={
            "archive_slug": archive.slug,
            "pk": ai.pk,
            "interface_slug": ci.slug,
        },
        follow=True,
        user=editor,
    )
    assert response.status_code == 200

    assert ci.slug in response.rendered_content

    assert f'id="id_{ci.slug}" checked' in response.rendered_content

    assert Job.objects.count() == 0

    alg = AlgorithmFactory()
    AlgorithmImageFactory(
        algorithm=alg, is_manifest_valid=True, is_in_registry=True
    )
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
                reverse_kwargs={
                    "archive_slug": archive.slug,
                    "pk": ai.pk,
                    "interface_slug": ci.slug,
                },
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
                reverse_kwargs={
                    "archive_slug": archive.slug,
                    "pk": ai.pk,
                    "interface_slug": ci.slug,
                },
                data={ci.slug: True},
                follow=True,
                user=editor,
            )

    # New jobs should be created as there is a new CIV
    assert Job.objects.count() == 3
    assert ComponentInterfaceValue.objects.count() == civ_count + 2


@pytest.mark.django_db
def test_archive_items_to_reader_study_update_form(client, settings):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)
    archive = ArchiveFactory()
    rs = ReaderStudyFactory()

    editor, reader = UserFactory(), UserFactory()
    archive.editors_group.user_set.add(editor)
    rs.add_editor(editor)
    rs.add_reader(reader)

    im1, im2, im3, im4 = ImageFactory.create_batch(4)
    overlay = ComponentInterface.objects.get(slug="generic-overlay")
    image = ComponentInterface.objects.get(slug="generic-medical-image")

    civ1, civ2, civ3, civ4 = (
        ComponentInterfaceValueFactory(interface=image, image=im1),
        ComponentInterfaceValueFactory(interface=image, image=im2),
        ComponentInterfaceValueFactory(interface=overlay, image=im3),
        ComponentInterfaceValueFactory(interface=overlay, image=im4),
    )

    ai1 = ArchiveItemFactory(archive=archive)
    ai2 = ArchiveItemFactory(archive=archive)

    ai1.values.add(civ1)
    ai2.values.add(civ2)

    assert rs.display_sets.count() == 0

    response = get_view_for_user(
        viewname="archives:items-reader-study-update",
        client=client,
        method=client.post,
        data={"items": [ai1.pk, ai2.pk], "reader_study": rs.pk},
        reverse_kwargs={"slug": archive.slug},
        follow=True,
        user=reader,
    )

    assert response.status_code == 403
    assert rs.display_sets.count() == 0

    response = get_view_for_user(
        viewname="archives:items-reader-study-update",
        client=client,
        method=client.post,
        data={"items": [ai1.pk, ai2.pk], "reader_study": rs.pk},
        reverse_kwargs={"slug": archive.slug},
        follow=True,
        user=editor,
    )

    assert response.status_code == 200
    assert rs.display_sets.count() == 2
    assert sorted(
        list(rs.display_sets.values_list("values", flat=True))
    ) == sorted([civ1.pk, civ2.pk])

    ai1.values.add(civ3)
    ai2.values.add(civ4)

    response = get_view_for_user(
        viewname="archives:items-reader-study-update",
        client=client,
        method=client.post,
        data={"items": [ai1.pk, ai2.pk], "reader_study": rs.pk},
        reverse_kwargs={"slug": archive.slug},
        follow=True,
        user=editor,
    )

    assert response.status_code == 200
    assert rs.display_sets.count() == 4
    assert sorted(
        sorted(list(ds.values.values_list("pk", flat=True)))
        for ds in rs.display_sets.all()
    ) == sorted([[civ1.pk], [civ2.pk], [civ1.pk, civ3.pk], [civ2.pk, civ4.pk]])
