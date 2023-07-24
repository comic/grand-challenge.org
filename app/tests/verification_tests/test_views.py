import pytest
from guardian.shortcuts import assign_perm

from grandchallenge.verifications.models import VerificationUserSet
from tests.factories import UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_verification_user_set_permissions(client):
    verification_user_set = VerificationUserSet.objects.create()
    user = UserFactory()

    response = get_view_for_user(
        client=client,
        viewname="verifications:verification-user-set-detail",
        reverse_kwargs={"pk": verification_user_set.pk},
        user=user,
    )
    assert response.status_code == 403

    assign_perm("verifications.view_verificationuserset", user)

    response = get_view_for_user(
        client=client,
        viewname="verifications:verification-user-set-detail",
        reverse_kwargs={"pk": verification_user_set.pk},
        user=user,
    )
    assert response.status_code == 200
