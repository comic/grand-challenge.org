import pytest


from tests.algorithms_tests.factories import AlgorithmFactory
from tests.factories import UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_algorithm_list_view(client):
    w1, w2 = AlgorithmFactory(), AlgorithmFactory()
    user = UserFactory(is_staff=True)

    response = get_view_for_user(
        viewname="algorithms:list", client=client, user=user
    )

    assert w1.get_absolute_url() in response.rendered_content
    assert w2.get_absolute_url() in response.rendered_content

    w1.delete()

    response = get_view_for_user(
        viewname="algorithms:list", client=client, user=user
    )

    assert w1.get_absolute_url() not in response.rendered_content
    assert w2.get_absolute_url() in response.rendered_content
