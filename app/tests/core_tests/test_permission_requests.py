import pytest
from actstream.actions import is_following
from actstream.models import Follow

from grandchallenge.algorithms.models import AlgorithmPermissionRequest
from grandchallenge.archives.models import ArchivePermissionRequest
from grandchallenge.notifications.models import Notification
from grandchallenge.reader_studies.models import ReaderStudyPermissionRequest
from grandchallenge.subdomains.utils import reverse
from tests.algorithms_tests.factories import AlgorithmFactory
from tests.archives_tests.factories import ArchiveFactory
from tests.factories import UserFactory
from tests.reader_studies_tests.factories import ReaderStudyFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
@pytest.mark.parametrize(
    "factory,namespace,request_model,request_attr,group_test",
    (
        (
            AlgorithmFactory,
            "algorithms",
            AlgorithmPermissionRequest,
            "algorithm",
            "is_user",
        ),
        (
            ReaderStudyFactory,
            "reader-studies",
            ReaderStudyPermissionRequest,
            "reader_study",
            "is_reader",
        ),
        (
            ArchiveFactory,
            "archives",
            ArchivePermissionRequest,
            "archive",
            "is_user",
        ),
    ),
)
def test_permission_request_workflow(
    client, factory, namespace, request_model, request_attr, group_test
):
    base_object = factory()
    user = UserFactory()
    permission_create_url = reverse(
        f"{namespace}:permission-request-create",
        kwargs={"slug": base_object.slug},
    )
    assert request_model.objects.count() == 0
    assert not getattr(base_object, group_test)(user)

    # Check the detail view redirects to permission create view
    response = get_view_for_user(
        client=client, user=user, url=base_object.get_absolute_url()
    )
    assert response.status_code == 302
    assert response.url == permission_create_url

    # Check the permission create view is viewable
    response = get_view_for_user(
        client=client, user=user, url=permission_create_url
    )
    assert response.status_code == 200

    # Create the permission request
    response = get_view_for_user(
        client=client,
        user=user,
        url=permission_create_url,
        method=client.post,
    )
    assert response.status_code == 302

    # Check the permission request object was created
    pr = request_model.objects.get()
    assert pr.status == request_model.PENDING
    assert pr.user == user
    assert getattr(pr, request_attr) == base_object

    # Check the detail view should still redirect to the permission create view
    response = get_view_for_user(
        client=client, user=user, url=base_object.get_absolute_url()
    )
    assert response.status_code == 302
    assert response.url == permission_create_url

    # Making a second permission request create should fail
    response = get_view_for_user(
        client=client,
        user=user,
        url=permission_create_url,
        method=client.post,
    )
    assert response.status_code == 200

    # The permission update url should not be viewable by this user
    permission_update_url = reverse(
        f"{namespace}:permission-request-update",
        kwargs={"slug": base_object.slug, "pk": pr.pk},
    )
    response = get_view_for_user(
        client=client, user=user, url=permission_update_url
    )
    assert response.status_code == 403

    # But this user should not be able to change it
    response = get_view_for_user(
        client=client,
        user=user,
        url=permission_update_url,
        method=client.post,
        data={"status": pr.ACCEPTED},
    )
    assert response.status_code == 403
    pr.refresh_from_db()
    assert pr.status == request_model.PENDING

    # New users should not be able to see the permission request status
    editor = UserFactory()
    response = get_view_for_user(
        client=client, user=editor, url=permission_update_url
    )
    assert response.status_code == 403

    # The new user should not be able to change it
    response = get_view_for_user(
        client=client,
        user=editor,
        url=permission_update_url,
        method=client.post,
        data={"status": pr.ACCEPTED},
    )
    assert response.status_code == 403
    pr.refresh_from_db()
    assert pr.status == request_model.PENDING

    # But they should be able to change it when they are made an editor
    base_object.add_editor(editor)
    response = get_view_for_user(
        client=client,
        user=editor,
        url=permission_update_url,
        method=client.post,
        data={"status": pr.ACCEPTED},
    )
    assert response.status_code == 302
    pr.refresh_from_db()
    assert pr.status == request_model.ACCEPTED

    # By now they should be added to the correct group
    assert getattr(base_object, group_test)(user)

    # The editor can also remove them later
    response = get_view_for_user(
        client=client,
        user=editor,
        url=permission_update_url,
        method=client.post,
        data={"status": pr.REJECTED},
    )
    assert response.status_code == 302
    pr.refresh_from_db()
    assert pr.status == request_model.REJECTED
    assert not getattr(base_object, group_test)(user)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "factory,namespace,request_model,request_attr",
    (
        (
            AlgorithmFactory,
            "algorithms",
            AlgorithmPermissionRequest,
            "algorithm",
        ),
        (
            ReaderStudyFactory,
            "reader-studies",
            ReaderStudyPermissionRequest,
            "reader_study",
        ),
        (ArchiveFactory, "archives", ArchivePermissionRequest, "archive",),
    ),
)
def test_permission_request_notifications_flow(
    client, factory, namespace, request_model, request_attr
):
    base_object = factory()
    editor = UserFactory()
    user = UserFactory()
    base_object.add_editor(editor)

    permission_create_url = reverse(
        f"{namespace}:permission-request-create",
        kwargs={"slug": base_object.slug},
    )

    assert request_model.objects.count() == 0
    assert base_object.editors_group.user_set.count() == 1
    # editors automatically follow the base_obj
    assert is_following(user=editor, obj=base_object)

    # Create the permission request
    _ = get_view_for_user(
        client=client,
        user=user,
        url=permission_create_url,
        method=client.post,
    )

    pr = request_model.objects.get()
    assert pr.status == request_model.PENDING
    assert pr.user == user
    # check that requester follows the request object
    assert is_following(user=user, obj=pr)
    # check request results in notification for followers of base_obj
    assert Notification.objects.count() == 1
    assert Notification.objects.get().user == editor
    assert f"{user.username} requested access to {base_object.title}" in str(
        Notification.objects.get().action
    )

    permission_update_url = reverse(
        f"{namespace}:permission-request-update",
        kwargs={"slug": base_object.slug, "pk": pr.pk},
    )
    # accept permission request
    _ = get_view_for_user(
        client=client,
        user=editor,
        url=permission_update_url,
        method=client.post,
        data={"status": pr.ACCEPTED},
    )

    pr.refresh_from_db()
    assert pr.status == request_model.ACCEPTED

    # check that status update results in notification for follower of request object
    assert Notification.objects.all()[1].user == user
    assert f"{pr} was accepted" in str(Notification.objects.all()[1].action)

    # reject permission request
    _ = get_view_for_user(
        client=client,
        user=editor,
        url=permission_update_url,
        method=client.post,
        data={"status": pr.REJECTED},
    )

    pr.refresh_from_db()
    assert pr.status == request_model.REJECTED
    assert Notification.objects.all()[2].user == user
    assert f"{pr} was rejected" in str(Notification.objects.all()[2].action)

    # when pr is deleted, the follows associated with it are too
    pr.delete()
    assert not Follow.objects.filter(object_id=pr.pk)

    # when editor is removed from base_obj, they no longer receive notifications about new requests
    Notification.objects.all().delete()
    assert Notification.objects.count() == 0
    base_object.remove_editor(editor)
    user2 = UserFactory()
    _ = get_view_for_user(
        client=client,
        user=user2,
        url=permission_create_url,
        method=client.post,
    )
    assert Notification.objects.count() == 0

    # when the base_obj is deleted, the follows are deleted as well
    base_object.delete()
    assert not Follow.objects.filter(object_id=base_object.pk)
