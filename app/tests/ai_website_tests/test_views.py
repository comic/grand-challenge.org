import pytest

from tests.ai_website_tests.factories import (
    CompanyEntryFactory,
    ProductEntryFactory,
)
from tests.factories import UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_product_list(client):
    product = ProductEntryFactory()
    user = UserFactory(is_superuser=True)

    response = get_view_for_user(
        viewname="ai-website:product_list",
        client=client,
        follow=True,
        user=user,
    )

    assert response.status_code == 200
    assert product.product_name in response.rendered_content


@pytest.mark.django_db
def test_product_detail(client):
    product = ProductEntryFactory()
    user = UserFactory(is_superuser=True)

    response = get_view_for_user(
        viewname="ai-website:product_page",
        reverse_kwargs={"pk": product.pk},
        client=client,
        follow=True,
        user=user,
    )

    assert response.status_code == 200
    assert product.product_name in response.rendered_content


@pytest.mark.django_db
def test_company_list(client):
    company = CompanyEntryFactory()
    user = UserFactory(is_superuser=True)

    response = get_view_for_user(
        viewname="ai-website:company_list",
        client=client,
        follow=True,
        user=user,
    )

    assert response.status_code == 200
    assert company.company_name in response.rendered_content


@pytest.mark.django_db
def test_company_detail(client):
    company = CompanyEntryFactory()
    user = UserFactory(is_superuser=True)

    response = get_view_for_user(
        viewname="ai-website:company_page",
        reverse_kwargs={"pk": company.pk},
        client=client,
        follow=True,
        user=user,
    )

    assert response.status_code == 200
    assert company.company_name in response.rendered_content
