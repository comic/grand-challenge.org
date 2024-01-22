import pytest
from django.forms import ModelForm
from guardian.shortcuts import assign_perm

from grandchallenge.hanging_protocols.forms import HangingProtocolForm
from grandchallenge.hanging_protocols.models import HangingProtocol
from tests.components_tests.factories import ComponentInterfaceFactory
from tests.factories import UserFactory
from tests.hanging_protocols_tests.factories import HangingProtocolFactory
from tests.hanging_protocols_tests.test_models import HangingProtocolTestModel
from tests.utils import get_view_for_user


class ViewContentTestForm(ModelForm):
    class Meta:
        model = HangingProtocolTestModel
        fields = ("view_content", "hanging_protocol")


@pytest.mark.django_db
def test_view_content_mixin():
    form = ViewContentTestForm(data={"view_content": [{}]})

    assert not form.is_valid()
    assert "JSON does not fulfill schema" in form.errors["view_content"][0]

    form = ViewContentTestForm(data={"view_content": {"main": ["test"]}})

    assert not form.is_valid()
    assert form.errors == {
        "__all__": [
            "Unknown interfaces in view content for viewport main: test"
        ]
    }

    i = ComponentInterfaceFactory(title="Test")
    hp = HangingProtocolFactory(json=[{"viewport_name": "main"}])

    form = ViewContentTestForm(
        data={
            "view_content": {"secondary": [i.slug]},
            "hanging_protocol": hp.pk,
        }
    )

    assert not form.is_valid()
    assert form.errors == {
        "__all__": [
            "Image ports in view_content do not match those in the selected hanging protocol."
        ]
    }

    form = ViewContentTestForm(
        data={"view_content": {"main": ["test"]}, "hanging_protocol": hp.pk}
    )
    assert form.is_valid()


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
            "json": '[{"viewport_name": "main", "parent_id": "main", "specialized_view": "intensity-over-time-chart"}, {"viewport_name": "secondary"}]',
        }
    )
    assert (
        "Viewport main has itself set as parent_id. Choose a different viewport as parent_id."
        in form.errors["json"]
    )

    form = HangingProtocolForm(
        {
            "title": "main",
            "json": '[{"viewport_name": "main", "parent_id": "secondary", "specialized_view": "intensity-over-time-chart"}, {"viewport_name": "secondary"}]',
        }
    )
    assert form.is_valid()

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


def test_hanging_protocol_clientside():
    form = HangingProtocolForm(
        {
            "title": "main",
            "json": '[{"specialized_view": "clientside", "viewport_name": "main"}]',
        }
    )
    assert form.is_valid()
