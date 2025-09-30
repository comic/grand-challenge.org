import pytest
from actstream.actions import follow, is_following
from actstream.models import Follow
from django.utils.html import format_html

from grandchallenge.algorithms.models import AlgorithmPermissionRequest
from grandchallenge.archives.models import ArchivePermissionRequest
from grandchallenge.core.utils.access_requests import (
    AccessRequestHandlingOptions,
)
from grandchallenge.notifications.models import Notification
from grandchallenge.participants.models import RegistrationRequest
from grandchallenge.profiles.templatetags.profiles import user_profile_link
from grandchallenge.reader_studies.models import ReaderStudyPermissionRequest
from grandchallenge.subdomains.utils import reverse
from grandchallenge.verifications.models import Verification
from tests.algorithms_tests.factories import AlgorithmFactory
from tests.archives_tests.factories import ArchiveFactory
from tests.factories import ChallengeFactory, UserFactory
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
        (
            ChallengeFactory,
            "participants",
            RegistrationRequest,
            "challenge",
            "is_participant",
        ),
    ),
)
def test_permission_request_workflow(
    client, factory, namespace, request_model, request_attr, group_test
):
    base_object = factory(
        access_request_handling=AccessRequestHandlingOptions.MANUAL_REVIEW
    )
    if namespace == "participants":
        permission_create_url = reverse(
            f"{namespace}:registration-create",
            kwargs={"challenge_short_name": base_object.short_name},
        )
    else:
        permission_create_url = reverse(
            f"{namespace}:permission-request-create",
            kwargs={"slug": base_object.slug},
        )

    user = UserFactory()

    assert request_model.objects.count() == 0
    assert not getattr(base_object, group_test)(user)

    # Check the detail view redirects to permission create view for algorithms, archives, reader studies
    if not namespace == "participants":
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

    post_data = None
    if namespace == "participants":
        post_data = {
            "registration_question_answers-TOTAL_FORMS": "0",
            "registration_question_answers-INITIAL_FORMS": "0",
            "registration_question_answers-MIN_NUM_FORMS": "0",
            "registration_question_answers-MAX_NUM_FORMS": "0",
        }

    # Create the permission request
    response = get_view_for_user(
        client=client,
        user=user,
        url=permission_create_url,
        method=client.post,
        data=post_data,
    )
    assert response.status_code == 302

    # Check the permission request object was created
    pr = request_model.objects.get()
    assert pr.status == request_model.PENDING
    assert pr.user == user
    assert getattr(pr, request_attr) == base_object

    # Check the detail view should still redirect to the permission create view
    if not namespace == "participants":
        response = get_view_for_user(
            client=client, user=user, url=base_object.get_absolute_url()
        )
        assert response.status_code == 302
        assert response.url == permission_create_url

    # Making a second permission request create should fail
    response = get_view_for_user(
        client=client, user=user, url=permission_create_url, method=client.post
    )
    assert response.status_code == 200

    # The permission update url should not be viewable by this user
    if namespace == "participants":
        permission_update_url = reverse(
            f"{namespace}:registration-update",
            kwargs={
                "challenge_short_name": base_object.short_name,
                "pk": pr.pk,
            },
        )
    else:
        permission_update_url = reverse(
            f"{namespace}:permission-request-update",
            kwargs={"slug": base_object.slug, "pk": pr.pk},
        )

    response = get_view_for_user(
        client=client, user=user, url=permission_update_url
    )
    assert response.status_code == 403

    # This user should not be able to change it
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
    if namespace == "participants":
        base_object.add_admin(editor)
    else:
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
        (ArchiveFactory, "archives", ArchivePermissionRequest, "archive"),
        (ChallengeFactory, "participants", RegistrationRequest, "challenge"),
    ),
)
def test_permission_request_notifications_flow_for_manual_review(
    client, factory, namespace, request_model, request_attr
):
    base_object = factory(
        access_request_handling=AccessRequestHandlingOptions.MANUAL_REVIEW
    )
    if namespace == "participants":
        permission_create_url = reverse(
            f"{namespace}:registration-create",
            kwargs={"challenge_short_name": base_object.short_name},
        )
        assert base_object.admins_group.user_set.count() == 1
        editor = base_object.admins_group.user_set.get()
        # challenge creation results in a notification, delete this notification
        Notification.objects.all().delete()
    else:
        editor = UserFactory()
        base_object.add_editor(editor)
        permission_create_url = reverse(
            f"{namespace}:permission-request-create",
            kwargs={"slug": base_object.slug},
        )
        assert base_object.editors_group.user_set.count() == 1

    user = UserFactory()
    assert request_model.objects.count() == 0
    # editors automatically follow the base_obj
    assert is_following(user=editor, obj=base_object)

    # Create the permission request
    _ = get_view_for_user(
        client=client,
        user=user,
        url=permission_create_url,
        method=client.post,
        data={
            "registration_question_answers-TOTAL_FORMS": "0",
            "registration_question_answers-INITIAL_FORMS": "0",
            "registration_question_answers-MIN_NUM_FORMS": "0",
            "registration_question_answers-MAX_NUM_FORMS": "0",
        },
    )

    pr = request_model.objects.get()
    assert pr.status == request_model.PENDING
    assert pr.user == user
    # check that requester follows the request object
    assert is_following(user=user, obj=pr)
    # check request results in notification for followers of base_obj
    assert Notification.objects.count() == 1
    assert Notification.objects.get().user == editor
    base_obj_str = format_html(
        '<a href="{}">{}</a>', base_object.get_absolute_url(), base_object
    )
    assert (
        f"{user_profile_link(user)} requested access to {base_obj_str}"
        in Notification.objects.get().print_notification(user=editor)
    )

    if namespace == "participants":
        permission_update_url = reverse(
            f"{namespace}:registration-update",
            kwargs={
                "challenge_short_name": base_object.short_name,
                "pk": pr.pk,
            },
        )
    else:
        permission_update_url = reverse(
            f"{namespace}:permission-request-update",
            kwargs={"slug": base_object.slug, "pk": pr.pk},
        )

    # accepting the permission request
    _ = get_view_for_user(
        client=client,
        user=editor,
        url=permission_update_url,
        method=client.post,
        data={"status": pr.ACCEPTED},
    )

    pr.refresh_from_db()
    assert pr.status == request_model.ACCEPTED

    # check that status update results in notification for follower of request object,
    # and removal of the notification for the editor
    user_notification = Notification.objects.get()
    assert user_notification.user == user
    assert (
        f"Your registration request for {base_obj_str} was accepted"
        in user_notification.print_notification(user=user)
    )

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
    assert Notification.objects.count() == 2
    new_user_notification = Notification.objects.exclude(
        id=user_notification.id
    ).get()
    assert new_user_notification.user == user
    assert (
        f"Your registration request for {base_obj_str} was rejected"
        in new_user_notification.print_notification(user=user)
    )


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
        (ArchiveFactory, "archives", ArchivePermissionRequest, "archive"),
        (ChallengeFactory, "participants", RegistrationRequest, "challenge"),
    ),
)
def test_permission_request_notifications_flow_for_accept_all(
    client, factory, namespace, request_model, request_attr
):
    # when access_request_handling is set to accept all,
    # no notifications are sent, no follows are created
    # and the request is automatically accepted
    base_object = factory(
        access_request_handling=AccessRequestHandlingOptions.ACCEPT_ALL
    )
    if namespace == "participants":
        permission_create_url = reverse(
            f"{namespace}:registration-create",
            kwargs={"challenge_short_name": base_object.short_name},
        )
        assert base_object.admins_group.user_set.count() == 1
        editor = base_object.admins_group.user_set.get()
        # challenge creation results in a notification, delete this notification
        Notification.objects.all().delete()
    else:
        editor = UserFactory()
        base_object.add_editor(editor)
        permission_create_url = reverse(
            f"{namespace}:permission-request-create",
            kwargs={"slug": base_object.slug},
        )
        assert base_object.editors_group.user_set.count() == 1

    user3 = UserFactory()
    _ = get_view_for_user(
        client=client,
        user=user3,
        url=permission_create_url,
        method=client.post,
        data={
            "registration_question_answers-TOTAL_FORMS": "0",
            "registration_question_answers-INITIAL_FORMS": "0",
            "registration_question_answers-MIN_NUM_FORMS": "0",
            "registration_question_answers-MAX_NUM_FORMS": "0",
        },
    )

    pr = request_model.objects.get()
    assert pr.status == request_model.ACCEPTED
    assert pr.user == user3
    assert not is_following(user=user3, obj=pr)
    assert Notification.objects.count() == 0


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
        (ArchiveFactory, "archives", ArchivePermissionRequest, "archive"),
        (ChallengeFactory, "participants", RegistrationRequest, "challenge"),
    ),
)
def test_permission_request_notifications_flow_for_accept_verified_users(
    client, factory, namespace, request_model, request_attr
):
    base_object = factory(
        access_request_handling=AccessRequestHandlingOptions.ACCEPT_VERIFIED_USERS
    )
    if namespace == "participants":
        permission_create_url = reverse(
            f"{namespace}:registration-create",
            kwargs={"challenge_short_name": base_object.short_name},
        )
        assert base_object.admins_group.user_set.count() == 1
        editor = base_object.admins_group.user_set.get()
        # challenge creation results in a notification, delete this notification
        Notification.objects.all().delete()
    else:
        editor = UserFactory()
        base_object.add_editor(editor)
        permission_create_url = reverse(
            f"{namespace}:permission-request-create",
            kwargs={"slug": base_object.slug},
        )
        assert base_object.editors_group.user_set.count() == 1

    not_verified_user = UserFactory()
    verified_user = UserFactory()
    Verification.objects.create(user=verified_user, is_verified=True)

    # the verified users gets accepted automatically, no follows and no notifcations
    _ = get_view_for_user(
        client=client,
        user=verified_user,
        url=permission_create_url,
        method=client.post,
        data={
            "registration_question_answers-TOTAL_FORMS": "0",
            "registration_question_answers-INITIAL_FORMS": "0",
            "registration_question_answers-MIN_NUM_FORMS": "0",
            "registration_question_answers-MAX_NUM_FORMS": "0",
        },
    )
    pr = request_model.objects.get()
    assert pr.status == request_model.ACCEPTED
    assert pr.user == verified_user
    assert not is_following(user=verified_user, obj=pr)
    assert Notification.objects.count() == 0
    pr.delete()

    # for the not verified user, a follow is created, the request is pending and
    # the admin gets a notification
    _ = get_view_for_user(
        client=client,
        user=not_verified_user,
        url=permission_create_url,
        method=client.post,
        data={
            "registration_question_answers-TOTAL_FORMS": "0",
            "registration_question_answers-INITIAL_FORMS": "0",
            "registration_question_answers-MIN_NUM_FORMS": "0",
            "registration_question_answers-MAX_NUM_FORMS": "0",
        },
    )
    pr = request_model.objects.get()
    assert pr.status == request_model.PENDING
    assert pr.user == not_verified_user
    assert is_following(user=not_verified_user, obj=pr)
    assert Notification.objects.count() == 1
    assert Notification.objects.get().user == editor


@pytest.mark.django_db
def test_algorithm_permission_request_notification_for_admins_only(client):
    base_object = AlgorithmFactory()
    editor = UserFactory()
    user = UserFactory()
    participant = UserFactory()
    base_object.add_editor(editor)
    base_object.add_user(participant)

    # create an algorithm job follow for participant
    follow(user=participant, obj=base_object, flag="job-active")

    permission_create_url = reverse(
        "algorithms:permission-request-create",
        kwargs={"slug": base_object.slug},
    )

    # Create the permission request
    _ = get_view_for_user(
        client=client,
        user=user,
        url=permission_create_url,
        method=client.post,
        data={
            "registration_question_answers-TOTAL_FORMS": "0",
            "registration_question_answers-INITIAL_FORMS": "0",
            "registration_question_answers-MIN_NUM_FORMS": "0",
            "registration_question_answers-MAX_NUM_FORMS": "0",
        },
    )

    assert Notification.objects.count() == 1
    assert Notification.objects.get().user == editor


@pytest.mark.django_db
def test_follows_deleted_when_request_deleted(client):
    base_object = AlgorithmFactory(
        access_request_handling=AccessRequestHandlingOptions.MANUAL_REVIEW
    )
    editor = UserFactory()
    base_object.add_editor(editor)
    permission_create_url = reverse(
        "algorithms:permission-request-create",
        kwargs={"slug": base_object.slug},
    )
    user = UserFactory()
    _ = get_view_for_user(
        client=client, user=user, url=permission_create_url, method=client.post
    )
    pr = AlgorithmPermissionRequest.objects.get()
    assert is_following(user, pr)
    pr.delete()
    assert not Follow.objects.filter(object_id=pr.pk)


@pytest.mark.django_db
def test_follows_deleted_when_base_obj_deleted(client):
    base_object = AlgorithmFactory(
        access_request_handling=AccessRequestHandlingOptions.MANUAL_REVIEW
    )
    editor = UserFactory()
    base_object.add_editor(editor)
    permission_create_url = reverse(
        "algorithms:permission-request-create",
        kwargs={"slug": base_object.slug},
    )
    user = UserFactory()
    _ = get_view_for_user(
        client=client,
        user=user,
        url=permission_create_url,
        method=client.post,
        data={
            "registration_question_answers-TOTAL_FORMS": "0",
            "registration_question_answers-INITIAL_FORMS": "0",
            "registration_question_answers-MIN_NUM_FORMS": "0",
            "registration_question_answers-MAX_NUM_FORMS": "0",
        },
    )
    pr = AlgorithmPermissionRequest.objects.get()
    assert is_following(user, pr)

    base_object.delete()
    assert not Follow.objects.filter(object_id=base_object.pk)
