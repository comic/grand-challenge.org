# -*- coding: utf-8 -*-

import pytest

from grandchallenge.core.urlresolvers import reverse
from tests.factories import UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_external_challenge_buttons(client):
    create_url = reverse("challenges:external-create")
    list_url = reverse("challenges:external-list")

    response = get_view_for_user(client=client, viewname="challenges:list")

    assert create_url not in response.rendered_content
    assert list_url not in response.rendered_content

    user = UserFactory()

    response = get_view_for_user(
        client=client, viewname="challenges:list", user=user,
    )

    assert create_url not in response.rendered_content
    assert list_url not in response.rendered_content

    staff_user = UserFactory(is_staff=True)

    response = get_view_for_user(
        client=client, viewname="challenges:list", user=staff_user,
    )

    assert create_url in response.rendered_content
    assert list_url in response.rendered_content
