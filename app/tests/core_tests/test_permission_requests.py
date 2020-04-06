import pytest

from grandchallenge.algorithms.models import AlgorithmPermissionRequest
from grandchallenge.archives.models import ArchivePermissionRequest
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
