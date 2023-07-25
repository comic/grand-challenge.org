import pytest
from django.core.exceptions import ValidationError
from guardian.shortcuts import assign_perm

from grandchallenge.hanging_protocols.forms import (
    HangingProtocolForm,
    ViewContentMixin,
)
from grandchallenge.hanging_protocols.models import HangingProtocol
from tests.components_tests.factories import ComponentInterfaceFactory
from tests.factories import UserFactory
from tests.hanging_protocols_tests.factories import HangingProtocolFactory
from tests.utils import get_view_for_user


class DummyForm(ViewContentMixin):
    cleaned_data = {"hanging_protocol": None}


@pytest.mark.django_db
def test_view_content_mixin():
    form = DummyForm()
    form.cleaned_data["view_content"] = [{}]
    with pytest.raises(ValidationError) as e:
        form.clean_view_content()

    assert "JSON does not fulfill schema" in e.value.message

    form.errors = {"view_content": []}
    form.cleaned_data["view_content"] = {"main": ["test"]}
    with pytest.raises(ValidationError) as e:
        form.clean_view_content()
    assert e.value.message == "Unkown slugs in view_content: test"

    form.errors = {"view_content": []}
    form.cleaned_data["hanging_protocol"] = HangingProtocolFactory(
        json=[{"viewport_name": "main"}]
    )
    form.cleaned_data["view_content"] = {"secondary": ["test"]}
    with pytest.raises(ValidationError) as e:
        form.clean_view_content()

    assert e.value.message == (
        "Image ports in view_content do not match those in the selected hanging protocol."
    )

    ComponentInterfaceFactory(title="Test")
    form.errors = {"view_content": []}
    form.cleaned_data["hanging_protocol"] = HangingProtocolFactory(
        json=[{"viewport_name": "main"}]
    )
    form.cleaned_data["view_content"] = {"main": ["test"]}
    form.clean_view_content()


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


def test_hanging_protocol_parent_id_draggable():
    form = HangingProtocolForm(
        {
            "title": "main",
            "json": '[{"viewport_name": "main", "parent_id": "foo", "draggable": true}]',
        }
    )
    assert (
        form.errors["json"][0]
        == "Viewport main has a parent_id that does not exist."
    )

    form = HangingProtocolForm(
        {
            "title": "main",
            "json": '[{"viewport_name": "main", "parent_id": "secondary"}, {"viewport_name": "secondary"}]',
        }
    )
    assert (
        form.errors["json"][0]
        == "Viewport main has a parent_id but is not draggable or is not a specialized view."
    )

    form = HangingProtocolForm(
        {
            "title": "main",
            "json": '[{"viewport_name": "main", "parent_id": "foo"}]',
        }
    )
    assert len(form.errors["json"]) == 2
    assert (
        "Viewport main has a parent_id that does not exist."
        in form.errors["json"]
    )
    assert (
        "Viewport main has a parent_id but is not draggable or is not a specialized view."
        in form.errors["json"]
    )

    form = HangingProtocolForm(
        {
            "title": "main",
            "json": '[{"viewport_name": "main", "parent_id": "secondary", "draggable": true}, {"viewport_name": "secondary"}]',
        }
    )
    assert form.is_valid()

    form = HangingProtocolForm(
        {
            "title": "main",
            "json": '[{"viewport_name": "main", "parent_id": "secondary", "specialized_view": "minimap"}, {"viewport_name": "secondary"}]',
        }
    )
    assert form.is_valid(), form.errors


def test_hanging_protocol_slice_plane_indicator():
    form = HangingProtocolForm(
        {
            "title": "main",
            "json": '[{"viewport_name": "main"}, {"viewport_name": "secondary", "slice_plane_indicator": "tertiary"}]',
        }
    )
    assert (
        form.errors["json"][0]
        == "Viewport secondary has a slice_plane_indicator that does not exist."
    )

    form = HangingProtocolForm(
        {
            "title": "main",
            "json": '[{"viewport_name": "main"}, {"viewport_name": "secondary", "slice_plane_indicator": "secondary"}]',
        }
    )
    assert (
        form.errors["json"][0]
        == "Viewport secondary has a slice_plane_indicator that is the same as the viewport_name."
    )

    form = HangingProtocolForm(
        {
            "title": "main",
            "json": '[{"viewport_name": "main"}, {"viewport_name": "secondary", "slice_plane_indicator": "main"}]',
        }
    )
    assert form.is_valid()


def test_hanging_protocol_openseadragon():
    form = HangingProtocolForm(
        {
            "title": "main",
            "json": '[{"specialized_view": "openseadragon", "viewport_name": "main"}]',
        }
    )
    assert form.is_valid()
