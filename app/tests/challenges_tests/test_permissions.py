import pytest
from guardian.shortcuts import assign_perm, remove_perm

from grandchallenge.subdomains.utils import reverse
from grandchallenge.verifications.models import Verification
from tests.factories import ExternalChallengeFactory, UserFactory
from tests.utils import (
    get_view_for_user,
    validate_admin_only_view,
    validate_logged_in_view,
)


@pytest.mark.django_db
@pytest.mark.parametrize("view", ["challenges:users-list"])
def test_challenge_logged_in_permissions(view, client, challenge_set):
    validate_logged_in_view(
        url=reverse(view), challenge_set=challenge_set, client=client
    )


@pytest.mark.django_db
def test_create_challenge_only_when_verified(client):
    user = UserFactory()
    assert not Verification.objects.filter(user=user)

    response = get_view_for_user(
        client=client, viewname="challenges:create", user=user
    )
    assert response.status_code == 403
    Verification.objects.create(user=user, is_verified=True)
    response = get_view_for_user(
        client=client, viewname="challenges:create", user=user
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_challenge_update_permissions(client, two_challenge_sets):
    validate_admin_only_view(
        two_challenge_set=two_challenge_sets, viewname="update", client=client
    )


@pytest.mark.django_db
class TestObjectPermissionRequiredViews:
    def test_permission_required_views(self, client):
        c = ExternalChallengeFactory()
        u = UserFactory()

        for view_name, kwargs, permission, obj in [
            ("create", {}, "challenges.add_externalchallenge", None),
            ("list", {}, "challenges.view_externalchallenge", None),
            (
                "update",
                {"short_name": c.short_name},
                "challenges.change_externalchallenge",
                None,  # NOTE: Using global perms
            ),
        ]:

            def _get_view():
                return get_view_for_user(
                    client=client,
                    viewname=f"challenges:external-{view_name}",
                    reverse_kwargs=kwargs,
                    user=u,
                )

            response = _get_view()
            assert response.status_code == 403

            assign_perm(permission, u, obj)

            response = _get_view()
            assert response.status_code == 200

            remove_perm(permission, u, obj)


@pytest.mark.django_db
def test_request_challenge_only_when_verified(client):
    user = UserFactory()
    assert not Verification.objects.filter(user=user)
    response = get_view_for_user(
        client=client, viewname="challenges:requests-create", user=user
    )
    assert response.status_code == 403
    Verification.objects.create(user=user, is_verified=True)
    response = get_view_for_user(
        client=client, viewname="challenges:create", user=user
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_view_and_update_challenge_request(
    client, challenge_reviewer, type_1_challenge_request
):
    # challenge request creator cannot view or update the request
    response = get_view_for_user(
        client=client,
        viewname="challenges:requests-detail",
        reverse_kwargs={"pk": type_1_challenge_request.pk},
        user=type_1_challenge_request.creator,
    )
    assert response.status_code == 403
    response = get_view_for_user(
        client=client,
        viewname="challenges:requests-update",
        reverse_kwargs={"pk": type_1_challenge_request.pk},
        user=type_1_challenge_request.creator,
    )
    assert response.status_code == 403

    # reviewer can view and udpate
    response = get_view_for_user(
        client=client,
        viewname="challenges:requests-detail",
        reverse_kwargs={"pk": type_1_challenge_request.pk},
        user=challenge_reviewer,
    )
    assert response.status_code == 200
    response = get_view_for_user(
        client=client,
        viewname="challenges:requests-update",
        reverse_kwargs={"pk": type_1_challenge_request.pk},
        user=challenge_reviewer,
    )
    assert response.status_code == 200
