import pytest

from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_product_list(client):
    response = get_view_for_user(url="/aiforradiology/", client=client)

    assert response.status_code == 302
    assert response.url == "https://www.example.com/"

    response = get_view_for_user(
        url="/aiforradiology/product/airs-medical-swiftmr", client=client
    )

    assert response.status_code == 302
    assert (
        response.url == "https://www.example.com/product/airs-medical-swiftmr"
    )
