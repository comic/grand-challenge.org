import pytest

from grandchallenge.hanging_protocols.views import HangingProtocolList
from tests.factories import UserFactory
from tests.hanging_protocols_tests.factories import HangingProtocolFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_hanging_protocol_list_view_pagination(client):
    user = UserFactory()
    HangingProtocolFactory.create_batch(HangingProtocolList.paginate_by + 1)

    response = get_view_for_user(
        client=client,
        method=client.get,
        viewname="hanging-protocols:list",
        user=user,
    )
    assert response.status_code == 200
    assert "Page 1 of 2" in response.rendered_content
