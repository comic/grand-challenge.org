import pytest
from actstream.actions import is_following
from django.contrib.auth.models import Permission

from grandchallenge.algorithms.models import Job
from grandchallenge.archives.forms import (
    ArchiveForm,
    ArchiveItemCreateForm,
    ArchiveItemUpdateForm,
)
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
    AlgorithmInterfaceFactory,
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
from tests.conftest import get_interface_form_data
from tests.factories import ImageFactory, UserFactory, WorkstationFactory
from tests.reader_studies_tests.factories import ReaderStudyFactory
from tests.utils import get_view_for_user, recurse_callbacks


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
@pytest.mark.parametrize(
    "form_class",
    (ArchiveItemCreateForm, ArchiveItemUpdateForm),
)
def test_archive_item_form_unique_title(form_class):
    archive1 = ArchiveFactory()

    user = UserFactory()
    archive1.add_editor(user)

    ai1 = ArchiveItemFactory(archive=archive1, title="Title in archive 1")

    instance1 = None
    if form_class == ArchiveItemUpdateForm:
        instance1 = ArchiveItemFactory(archive=archive1)

    # Adding a unique title in archive 1 is allowed
    form = form_class(
        user=user,
        instance=instance1,
        base_obj=archive1,
        data={
            "title": "A unique title",
        },
    )
    assert form.is_valid()

    # Adding an existing title in archive 1 is not allowed
    form = form_class(
        user=user,
        instance=instance1,
        base_obj=archive1,
        data={"title": ai1.title},
    )
    assert not form.is_valid()

    # However, it is allowed if it's in another archive all together
    archive2 = ArchiveFactory()
    archive2.add_editor(user)

    instance2 = None
    if form_class == ArchiveItemUpdateForm:
        instance2 = ArchiveItemFactory(archive=archive2)

    form = form_class(
        user=user,
        instance=instance2,
        base_obj=archive2,
        data={
            "title": ai1.title,
        },
    )
    assert form.is_valid()


@pytest.mark.django_db
def test_archive_item_update_permissions(client):
    archive = ArchiveFactory()

    editor = UserFactory()
    user = UserFactory()

    archive.add_editor(editor)
    ai = ArchiveItemFactory(archive=archive)

    # user cannot edit archive item
    response = get_view_for_user(
        viewname="archives:item-edit",
        client=client,
        method=client.get,
        reverse_kwargs={
            "slug": archive.slug,
            "pk": ai.pk,
        },
        user=user,
    )
    assert response.status_code == 403

    archive.add_uploader(user)
    response = get_view_for_user(
        viewname="archives:item-edit",
        client=client,
        method=client.get,
        reverse_kwargs={
            "slug": archive.slug,
            "pk": ai.pk,
        },
        user=user,
    )
    assert response.status_code == 200

    response = get_view_for_user(
        viewname="archives:item-edit",
        client=client,
        method=client.get,
        reverse_kwargs={
            "slug": archive.slug,
            "pk": ai.pk,
        },
        user=editor,
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_archive_item_update_triggers_algorithm_jobs(
    client, settings, django_capture_on_commit_callbacks
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    archive = ArchiveFactory()
    editor = UserFactory()
    archive.add_editor(editor)

    ci = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.BOOL
    )
    civ = ComponentInterfaceValueFactory(
        interface=ci, value=True, file=None, image=None
    )
    ai = ArchiveItemFactory(archive=archive)
    ai.values.add(civ)

    assert Job.objects.count() == 0

    alg = AlgorithmFactory()
    interface = AlgorithmInterfaceFactory(inputs=[ci])
    alg.interfaces.add(interface)
    AlgorithmImageFactory(
        algorithm=alg,
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
    )
    with django_capture_on_commit_callbacks(execute=True):
        archive.algorithms.add(alg)

    assert Job.objects.count() == 1

    civ_count = ComponentInterfaceValue.objects.count()

    with django_capture_on_commit_callbacks() as callbacks:
        get_view_for_user(
            viewname="archives:item-edit",
            client=client,
            method=client.post,
            reverse_kwargs={
                "slug": archive.slug,
                "pk": ai.pk,
            },
            data={
                **get_interface_form_data(interface_slug=ci.slug, data=False)
            },
            user=editor,
        )
    recurse_callbacks(
        callbacks=callbacks,
        django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
    )

    assert ai.values.filter(pk=civ.pk).count() == 0
    # This should create a new CIV as they are immutable
    assert ComponentInterfaceValue.objects.count() == civ_count + 1

    # A new job should have been created, because the value for 'bool'
    # has changed
    assert Job.objects.count() == 2

    with django_capture_on_commit_callbacks() as callbacks:
        get_view_for_user(
            viewname="archives:item-edit",
            client=client,
            method=client.post,
            reverse_kwargs={
                "slug": archive.slug,
                "pk": ai.pk,
            },
            data={
                **get_interface_form_data(interface_slug=ci.slug, data=True)
            },
            user=editor,
        )
    recurse_callbacks(
        callbacks=callbacks,
        django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
    )

    # No new jobs should be created since no new CIV was created
    assert Job.objects.count() == 2
    assert ComponentInterfaceValue.objects.count() == civ_count + 1

    # A change to the title should not fire-off a new job
    ai.title = "A new title"
    ai.save()
    assert Job.objects.count() == 2


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

    ai1 = ArchiveItemFactory(archive=archive, title="archive item 1")
    ai2 = ArchiveItemFactory(archive=archive, title="archive item 2")

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

    assert sorted([ds.title for ds in rs.display_sets.all()]) == sorted(
        [ai1.title, ai2.title]
    )
    assert sorted(
        list(rs.display_sets.values_list("values", flat=True))
    ) == sorted([civ1.pk, civ2.pk])

    ai1.title = "New title 1"
    ai1.values.add(civ3)
    ai1.save()

    ai2.title = "New title 2"
    ai2.values.add(civ4)
    ai2.save()

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


@pytest.mark.django_db
def test_archive_update_form_algorithm_queryset():
    alg1, alg2, alg3 = AlgorithmFactory.create_batch(3)
    user = UserFactory()
    for alg in [alg1, alg2]:
        alg.add_editor(user)
    archive = ArchiveFactory()

    AlgorithmImageFactory(
        algorithm=alg1,
        is_desired_version=True,
        is_manifest_valid=True,
        is_in_registry=True,
    )

    form = ArchiveForm(instance=archive, user=user)
    assert alg1 in form.fields["algorithms"].queryset
    assert alg2 not in form.fields["algorithms"].queryset
    assert alg3 not in form.fields["algorithms"].queryset
