import pytest
from guardian.shortcuts import assign_perm

from grandchallenge.hanging_protocols.forms import ViewContentMixin
from grandchallenge.hanging_protocols.models import HangingProtocol
from tests.components_tests.factories import ComponentInterfaceFactory
from tests.factories import UserFactory
from tests.hanging_protocols_tests.factories import HangingProtocolFactory
from tests.utils import get_view_for_user


class DummyForm(ViewContentMixin):
    cleaned_data = {"hanging_protocol": None}
    errors = {"view_content": []}

    def add_error(self, *, field, error):
        self.errors[field].append(error)


@pytest.mark.django_db
def test_view_content_mixin():
    form = DummyForm()
    form.cleaned_data["view_content"] = {"main": ["test"]}
    form.clean_view_content()
    assert "Unkown slugs in view_content: test" in form.errors["view_content"]

    form.errors = {"view_content": []}
    form.cleaned_data["hanging_protocol"] = HangingProtocolFactory(
        json=[{"viewport_name": "main"}]
    )
    form.cleaned_data["view_content"] = {"secondary": ["test"]}
    form.clean_view_content()

    assert (
        "Image ports in view_content do not match those in the selected hanging protocol."
        in form.errors["view_content"]
    )
    assert "Unkown slugs in view_content: test" in form.errors["view_content"]

    ComponentInterfaceFactory(title="Test")
    form.errors = {"view_content": []}
    form.cleaned_data["hanging_protocol"] = HangingProtocolFactory(
        json=[{"viewport_name": "main"}]
    )
    form.cleaned_data["view_content"] = {"main": ["test"]}
    form.clean_view_content()

    assert form.errors["view_content"] == []


@pytest.mark.django_db
def test_hanging_protocol_form(client):
    user = UserFactory()

    response = get_view_for_user(
        viewname="hanging-protocols:create",
        client=client,
        method=client.post,
        data={
            "title": "main",
            "json": '[{"viewport_name": "main"}, {"viewport_name": "main"}]',
        },
        follow=True,
        user=user,
    )

    assert response.status_code == 403
    assign_perm("hanging_protocols.add_hangingprotocol", user)

    assert HangingProtocol.objects.count() == 0

    response = get_view_for_user(
        viewname="hanging-protocols:create",
        client=client,
        method=client.post,
        data={
            "title": "main",
            "json": '[{"viewport_name": "main"}, {"viewport_name": "main"}]',
        },
        follow=True,
        user=user,
    )

    assert response.status_code == 200
    assert "Each viewport can only be used once." in response.rendered_content
    assert HangingProtocol.objects.count() == 0

    response = get_view_for_user(
        viewname="hanging-protocols:create",
        client=client,
        method=client.post,
        data={
            "title": "main",
            "json": '[{"viewport_name": "main"}, {"viewport_name": "secondary"}]',
        },
        follow=True,
        user=user,
    )

    assert response.status_code == 200
    assert (
        "Each viewport can only be used once." not in response.rendered_content
    )
    assert HangingProtocol.objects.count() == 1


@pytest.mark.django_db
def test_hanging_protocol_dimension_validation(client):
    user = UserFactory()
    assign_perm("hanging_protocols.add_hangingprotocol", user)

    response = get_view_for_user(
        viewname="hanging-protocols:create",
        client=client,
        method=client.post,
        data={
            "title": "main",
            "json": '[{"viewport_name": "main", "x": 0, "y": 0}]',
        },
        follow=True,
        user=user,
    )

    assert response.status_code == 200
    assert HangingProtocol.objects.count() == 0
    assert (
        "Either none or all viewports must have x, y, w, and h keys. Viewport main missing w, h."
        in response.rendered_content
    )

    response = get_view_for_user(
        viewname="hanging-protocols:create",
        client=client,
        method=client.post,
        data={
            "title": "main",
            "json": '[{"viewport_name": "main", "x": 0, "y": 0, "w": 1, "h": 1}, '
            '{"viewport_name": "secondary"}]',
        },
        follow=True,
        user=user,
    )

    assert response.status_code == 200
    assert HangingProtocol.objects.count() == 0
    assert (
        "Either none or all viewports must have x, y, w, and h keys. Viewport secondary missing x, y, w, h."
        in response.rendered_content
    )

    response = get_view_for_user(
        viewname="hanging-protocols:create",
        client=client,
        method=client.post,
        data={
            "title": "main",
            "json": '[{"viewport_name": "main", "x": 0, "y": 0, "w": 1, "h": 1}]',
        },
        follow=True,
        user=user,
    )

    assert response.status_code == 200
    assert HangingProtocol.objects.count() == 1
    assert (
        "Either none or all viewports must have x, y, w, and h keys."
        not in response.rendered_content
    )
