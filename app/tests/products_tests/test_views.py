import pytest
from guardian.utils import get_anonymous_user

from tests.products_tests.factories import (
    CompanyFactory,
    ProductFactory,
)
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_product_list(client):
    product = ProductFactory()

    response = get_view_for_user(
        viewname="products:product-list",
        client=client,
        follow=True,
        user=get_anonymous_user(),
    )

    assert response.status_code == 200
    assert product.product_name in response.rendered_content


@pytest.mark.django_db
def test_product_detail(client):
    product = ProductFactory()

    response = get_view_for_user(
        viewname="products:product-detail",
        reverse_kwargs={"pk": product.pk},
        client=client,
        follow=True,
        user=get_anonymous_user(),
    )

    assert response.status_code == 200
    assert product.product_name in response.rendered_content


@pytest.mark.django_db
def test_company_list(client):
    company = CompanyFactory()

    response = get_view_for_user(
        viewname="products:company-list",
        client=client,
        follow=True,
        user=get_anonymous_user(),
    )

    assert response.status_code == 200
    assert company.company_name in response.rendered_content


@pytest.mark.django_db
def test_company_detail(client):
    company = CompanyFactory()

    response = get_view_for_user(
        viewname="products:company-detail",
        reverse_kwargs={"pk": company.pk},
        client=client,
        follow=True,
        user=get_anonymous_user(),
    )

    assert response.status_code == 200
    assert company.company_name in response.rendered_content
