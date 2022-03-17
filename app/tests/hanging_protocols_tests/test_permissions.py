import pytest
from guardian.shortcuts import assign_perm

from tests.factories import UserFactory
from tests.hanging_protocols_tests.factories import HangingProtocolFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_permission_required_views(client):
    user = UserFactory()
    hp = HangingProtocolFactory()

    # anyone can view a hanging protocol and the list view
    response = get_view_for_user(
        viewname="hanging-protocols:list",
        client=client,
        user=user,
    )
    assert response.status_code == 200

    response = get_view_for_user(
        viewname="hanging-protocols:detail",
        client=client,
        user=user,
        reverse_kwargs={"slug": hp.slug},
    )
    assert response.status_code == 200

    # only users with the add.hangingprotocol permision can create one
    response = get_view_for_user(
        viewname="hanging-protocols:create",
        client=client,
        user=user,
    )
    assert response.status_code == 403

    assign_perm("hanging_protocols.add_hangingprotocol", user)
    response = get_view_for_user(
        viewname="hanging-protocols:create",
        client=client,
        user=user,
    )
    assert response.status_code == 200

    # only the creator can edit a hanging protocol
    response = get_view_for_user(
        viewname="hanging-protocols:update",
        client=client,
        user=hp.creator,
        reverse_kwargs={"slug": hp.slug},
    )
    assert response.status_code == 200

    response = get_view_for_user(
        viewname="hanging-protocols:update",
        client=client,
        user=user,
        reverse_kwargs={"slug": hp.slug},
    )
    assert response.status_code == 403
