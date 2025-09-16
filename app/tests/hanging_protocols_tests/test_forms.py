import json

import pytest
from django.forms import ModelForm
from django.utils.text import format_lazy
from guardian.shortcuts import assign_perm

from grandchallenge.algorithms.forms import AlgorithmForm
from grandchallenge.archives.forms import ArchiveForm
from grandchallenge.components.models import (
    InterfaceKind,
    InterfaceKindChoices,
)
from grandchallenge.core.utils.access_requests import (
    AccessRequestHandlingOptions,
)
from grandchallenge.evaluation.forms import PhaseUpdateForm
from grandchallenge.hanging_protocols.forms import HangingProtocolForm
from grandchallenge.hanging_protocols.models import HangingProtocol
from grandchallenge.reader_studies.forms import ReaderStudyUpdateForm
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmInterfaceFactory,
)
from tests.archives_tests.factories import ArchiveItemFactory
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.evaluation_tests.factories import PhaseFactory
from tests.factories import UserFactory, WorkstationFactory
from tests.hanging_protocols_tests.factories import HangingProtocolFactory
from tests.hanging_protocols_tests.test_models import HangingProtocolTestModel
from tests.reader_studies_tests.factories import DisplaySetFactory
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
        "__all__": ["Unknown sockets in view content for viewport main: test"]
    }

    i = ComponentInterfaceFactory(
        title="Test", kind=InterfaceKindChoices.STRING
    )
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


@pytest.mark.django_db
@pytest.mark.parametrize(
    "hanging_protocol_json, form_is_valid, expected_json_error",
    (
        ("[]", False, "This field is required."),
        ("{}", False, "This field is required."),
        (
            '[{"viewport_name": "main"}]',
            True,
            None,
        ),
        (
            12345,
            False,
            "Hanging protocol definition is invalid. Have a look at the example in the helptext.",
        ),
        ("main", False, "Enter a valid JSON."),
        (
            "[1,2,3,4,5]",
            False,
            "Hanging protocol definition is invalid. Have a look at the example in the helptext.",
        ),
        (
            '["test1", "test2", "test3"]',
            False,
            "Hanging protocol definition is invalid. Have a look at the example in the helptext.",
        ),
        (
            "[[],[],[]]",
            False,
            "Hanging protocol definition is invalid. Have a look at the example in the helptext.",
        ),
        (
            "[{},{},{}]",
            False,
            "Hanging protocol definition is invalid. Have a look at the example in the helptext.",
        ),
        (
            "true",
            False,
            "Hanging protocol definition is invalid. Have a look at the example in the helptext.",
        ),
        (
            "false",
            False,
            "Hanging protocol definition is invalid. Have a look at the example in the helptext.",
        ),
        (
            '{"viewport_name": "main"}',
            False,
            "Hanging protocol definition is invalid. Have a look at the example in the helptext.",
        ),
        (
            "[{}]",
            False,
            "Hanging protocol definition is invalid. Have a look at the example in the helptext.",
        ),
        (
            '[{"test":1}]',
            False,
            "Hanging protocol definition is invalid. Have a look at the example in the helptext.",
        ),
        (
            '[{"test1":"main"},{"test2":"secondary"}]',
            False,
            "Hanging protocol definition is invalid. Have a look at the example in the helptext.",
        ),
        (
            '[{"viewport_name": "main", "label": "~test"}]',
            False,
            "JSON does not fulfill schema: instance '~test' does not match '^[a-zA-Z0-9 -]*$'",
        ),
    ),
)
def test_hanging_protocol_form_json_validation(
    hanging_protocol_json, form_is_valid, expected_json_error
):
    form = HangingProtocolForm(
        {
            "title": "main",
            "json": hanging_protocol_json,
        }
    )
    assert form.is_valid() is form_is_valid
    assert form.errors.get("json", [None])[0] == expected_json_error


def make_ci_list(
    *,
    number_of_images,
    number_of_overlays,
    number_of_isolated_interfaces,
    number_of_undisplayable_interfaces,
):
    ci_list = []

    for i in range(number_of_isolated_interfaces):
        ci = ComponentInterfaceFactory(
            kind=InterfaceKindChoices.CHART,
            title=f"test-ci-isolated-{i}",
        )
        ci_list.append(ci)

    for i in range(number_of_images):
        ci = ComponentInterfaceFactory(
            kind=InterfaceKindChoices.IMAGE,
            title=f"test-ci-image-{i}",
        )
        ci_list.append(ci)

    for i in range(number_of_overlays):
        ci = ComponentInterfaceFactory(
            kind=InterfaceKindChoices.SEGMENTATION,
            title=f"test-ci-overlay-{i}",
        )
        ci_list.append(ci)

    for i in range(number_of_undisplayable_interfaces):
        ci = ComponentInterfaceFactory(
            kind=InterfaceKind.InterfaceKindChoices.ZIP,
            title=f"test-ci-undisplayable-{i}",
        )
        ci_list.append(ci)

    return ci_list


@pytest.mark.parametrize(
    "number_of_images,number_of_overlays,number_of_isolated_interfaces,number_of_undisplayable_interfaces,expected_help_text",
    (
        (
            0,
            0,
            0,
            0,
            (
                "No sockets of type image, chart, pdf, mp4, thumbnail_jpg or thumbnail_png are used. At least one socket of those types is needed to configure the viewer. "
                'Refer to the <a href="https://testserver/documentation/viewer-content/">documentation</a> for more information'
            ),
        ),
        (
            0,
            1,
            0,
            1,
            (
                "The following sockets are used in your {}: test-ci-overlay-0 and test-ci-undisplayable-0. "
                "No sockets of type image, chart, pdf, mp4, thumbnail_jpg or thumbnail_png are used. At least one socket of those types is needed to configure the viewer. "
                'Refer to the <a href="https://testserver/documentation/viewer-content/">documentation</a> for more information'
            ),
        ),
        (
            1,
            1,
            1,
            1,
            (
                "The following sockets are used in your {}: test-ci-isolated-0, test-ci-image-0, test-ci-overlay-0, and test-ci-undisplayable-0. "
                'Example usage: {{"main": ["test-ci-isolated-0"], "secondary": ["test-ci-image-0", "test-ci-overlay-0"]}}. '
                'Refer to the <a href="https://testserver/documentation/viewer-content/">documentation</a> for more information'
            ),
        ),
    ),
)
@pytest.mark.parametrize(
    "object_factory,form_class",
    (
        (ArchiveItemFactory, ArchiveForm),
        (DisplaySetFactory, ReaderStudyUpdateForm),
    ),
)
@pytest.mark.django_db
def test_archive_and_reader_study_forms_view_content_help_text(
    number_of_images,
    number_of_overlays,
    number_of_isolated_interfaces,
    number_of_undisplayable_interfaces,
    expected_help_text,
    object_factory,
    form_class,
):
    ci_list = make_ci_list(
        number_of_images=number_of_images,
        number_of_overlays=number_of_overlays,
        number_of_isolated_interfaces=number_of_isolated_interfaces,
        number_of_undisplayable_interfaces=number_of_undisplayable_interfaces,
    )
    civ_list = [ComponentInterfaceValueFactory(interface=ci) for ci in ci_list]

    instance = object_factory()
    instance.values.set(civ_list)

    form = form_class(user=UserFactory(), instance=instance.base_object)

    assert form.fields["view_content"].help_text == format_lazy(
        expected_help_text, instance.base_object._meta.verbose_name
    )


@pytest.mark.parametrize(
    "number_of_images,number_of_overlays,number_of_isolated_interfaces,number_of_undisplayable_interfaces,expected_help_text",
    (
        (
            0,
            0,
            0,
            0,
            (
                "No sockets of type image, chart, pdf, mp4, thumbnail_jpg or thumbnail_png are used. At least one socket of those types is needed to configure the viewer. "
                'Refer to the <a href="https://testserver/documentation/viewer-content/">documentation</a> for more information'
            ),
        ),
        (
            0,
            1,
            0,
            1,
            (
                "No sockets of type image, chart, pdf, mp4, thumbnail_jpg or thumbnail_png are used. At least one socket of those types is needed to configure the viewer. "
                'Refer to the <a href="https://testserver/documentation/viewer-content/">documentation</a> for more information'
            ),
        ),
        (
            1,
            1,
            1,
            1,
            (
                'Example usage: {"main": ["test-ci-isolated-0"], "secondary": ["test-ci-image-0", "test-ci-overlay-0"]}. '
                'Refer to the <a href="https://testserver/documentation/viewer-content/">documentation</a> for more information'
            ),
        ),
    ),
)
@pytest.mark.django_db
def test_algorithm_form_view_content_help_text(
    number_of_images,
    number_of_overlays,
    number_of_isolated_interfaces,
    number_of_undisplayable_interfaces,
    expected_help_text,
):
    ci_list = make_ci_list(
        number_of_images=number_of_images,
        number_of_overlays=number_of_overlays,
        number_of_isolated_interfaces=number_of_isolated_interfaces,
        number_of_undisplayable_interfaces=number_of_undisplayable_interfaces,
    )
    algorithm = AlgorithmFactory()
    if ci_list:
        interface = AlgorithmInterfaceFactory(
            inputs=ci_list[:-1], outputs=[ci_list[-1]]
        )
        algorithm.interfaces.set([interface])

    form = AlgorithmForm(user=UserFactory(), instance=algorithm)

    assert sorted(
        [interface.pk for interface in algorithm.linked_component_interfaces]
    ) == [interface.pk for interface in ci_list]
    assert expected_help_text in form.fields["view_content"].help_text


@pytest.mark.parametrize(
    "number_of_images,number_of_overlays,number_of_isolated_interfaces,number_of_undisplayable_interfaces,expected_help_text",
    (
        (
            0,
            0,
            0,
            0,
            (
                "No sockets of type image, chart, pdf, mp4, thumbnail_jpg or thumbnail_png are used. At least one socket of those types is needed to configure the viewer. "
                'Refer to the <a href="https://testserver/documentation/viewer-content/">documentation</a> for more information'
            ),
        ),
        (
            0,
            1,
            0,
            1,
            (
                "No sockets of type image, chart, pdf, mp4, thumbnail_jpg or thumbnail_png are used. At least one socket of those types is needed to configure the viewer. "
                'Refer to the <a href="https://testserver/documentation/viewer-content/">documentation</a> for more information'
            ),
        ),
        (
            1,
            1,
            1,
            1,
            (
                'Example usage: {"main": ["test-ci-isolated-0"], "secondary": ["test-ci-image-0", "test-ci-overlay-0"]}. '
                'Refer to the <a href="https://testserver/documentation/viewer-content/">documentation</a> for more information'
            ),
        ),
    ),
)
@pytest.mark.django_db
def test_phase_update_form_view_content_help_text(
    number_of_images,
    number_of_overlays,
    number_of_isolated_interfaces,
    number_of_undisplayable_interfaces,
    expected_help_text,
):
    ci_list = make_ci_list(
        number_of_images=number_of_images,
        number_of_overlays=number_of_overlays,
        number_of_isolated_interfaces=number_of_isolated_interfaces,
        number_of_undisplayable_interfaces=number_of_undisplayable_interfaces,
    )
    phase = PhaseFactory()
    if ci_list:
        interface = AlgorithmInterfaceFactory(
            inputs=ci_list[:-1], outputs=[ci_list[-1]]
        )
        phase.algorithm_interfaces.set([interface])

    form = PhaseUpdateForm(
        user=UserFactory(), instance=phase, **{"challenge": phase.challenge}
    )

    assert sorted(
        [interface.pk for interface in phase.linked_component_interfaces]
    ) == [interface.pk for interface in ci_list]
    assert expected_help_text in form.fields["view_content"].help_text


@pytest.mark.django_db
@pytest.mark.parametrize(
    "number_of_images,number_of_overlays,number_of_isolated_interfaces,expected_example_json",
    (
        (
            0,
            0,
            0,
            None,
        ),
        (
            2,
            0,
            0,
            {"main": ["test-ci-image-0"], "secondary": ["test-ci-image-1"]},
        ),
        (
            0,
            2,
            0,
            None,
        ),
        (
            5,
            5,
            0,
            {
                "main": ["test-ci-image-0", "test-ci-overlay-0"],
                "secondary": ["test-ci-image-1", "test-ci-overlay-1"],
                "tertiary": ["test-ci-image-2", "test-ci-overlay-2"],
                "quaternary": ["test-ci-image-3", "test-ci-overlay-3"],
                "quinary": ["test-ci-image-4", "test-ci-overlay-4"],
            },
        ),
        (
            6,
            3,
            1,
            {
                "main": ["test-ci-isolated-0"],
                "secondary": ["test-ci-image-0", "test-ci-overlay-0"],
                "tertiary": ["test-ci-image-1", "test-ci-overlay-1"],
                "quaternary": ["test-ci-image-2", "test-ci-overlay-2"],
                "quinary": ["test-ci-image-3"],
                "senary": ["test-ci-image-4"],
                "septenary": ["test-ci-image-5"],
            },
        ),
        (
            3,
            6,
            1,
            {
                "main": ["test-ci-isolated-0"],
                "secondary": [
                    "test-ci-image-0",
                    "test-ci-overlay-0",
                    "test-ci-overlay-1",
                ],
                "tertiary": [
                    "test-ci-image-1",
                    "test-ci-overlay-2",
                    "test-ci-overlay-3",
                ],
                "quaternary": [
                    "test-ci-image-2",
                    "test-ci-overlay-4",
                    "test-ci-overlay-5",
                ],
            },
        ),
        (
            3,
            8,
            1,
            {
                "main": ["test-ci-isolated-0"],
                "secondary": [
                    "test-ci-image-0",
                    "test-ci-overlay-0",
                    "test-ci-overlay-1",
                    "test-ci-overlay-2",
                ],
                "tertiary": [
                    "test-ci-image-1",
                    "test-ci-overlay-3",
                    "test-ci-overlay-4",
                    "test-ci-overlay-5",
                ],
                "quaternary": [
                    "test-ci-image-2",
                    "test-ci-overlay-6",
                    "test-ci-overlay-7",
                ],
            },
        ),
    ),
)
def test_generate_view_content_example(
    number_of_images,
    number_of_overlays,
    number_of_isolated_interfaces,
    expected_example_json,
):
    ci_list = make_ci_list(
        number_of_images=number_of_images,
        number_of_overlays=number_of_overlays,
        number_of_isolated_interfaces=number_of_isolated_interfaces,
        number_of_undisplayable_interfaces=0,
    )
    alg = AlgorithmFactory()
    if ci_list:
        interface = AlgorithmInterfaceFactory(
            inputs=ci_list[:-1], outputs=[ci_list[-1]]
        )
        alg.interfaces.set([interface])
    form = AlgorithmForm(user=UserFactory(), instance=alg)

    view_content_example = form.generate_view_content_example()
    view_content_example_json = (
        json.loads(view_content_example) if view_content_example else None
    )

    assert view_content_example_json == expected_example_json


@pytest.mark.django_db
@pytest.mark.parametrize(
    "hanging_protocol_json,view_content_example_json_expected_keys",
    (
        (None, {"main", "secondary", "tertiary", "quaternary"}),
        ([{}], {}),
        (
            [{"viewport_name": "main"}, {"viewport_name": "secondary"}],
            {"main", "secondary"},
        ),
        (
            [
                {"viewport_name": "main"},
                {"viewport_name": "secondary"},
                {"viewport_name": "tertiary"},
                {"viewport_name": "quaternary"},
            ],
            {"main", "secondary", "tertiary", "quaternary"},
        ),
        (
            [
                {"viewport_name": "main"},
                {"viewport_name": "secondary"},
                {"viewport_name": "tertiary"},
                {"viewport_name": "quaternary"},
                {"viewport_name": "quinary"},
            ],
            {"main", "secondary", "tertiary", "quaternary", "quinary"},
        ),
    ),
)
@pytest.mark.parametrize(
    "num_of_images,num_of_isolated_interfaces",
    (
        (4, 0),
        (1, 3),
        (2, 2),
        (3, 1),
        (0, 4),
    ),
)
def test_reader_study_forms_view_content_example_with_hanging_protocol(
    hanging_protocol_json,
    view_content_example_json_expected_keys,
    num_of_images,
    num_of_isolated_interfaces,
):
    ci_list = make_ci_list(
        number_of_images=num_of_images,
        number_of_overlays=2,
        number_of_isolated_interfaces=num_of_isolated_interfaces,
        number_of_undisplayable_interfaces=1,
    )
    civ_list = [ComponentInterfaceValueFactory(interface=ci) for ci in ci_list]

    instance = DisplaySetFactory()
    instance.values.set(civ_list)

    ws = WorkstationFactory()
    creator = UserFactory()
    ws.add_user(creator)

    form_data = {
        "title": "foo bar",
        "workstation": ws.pk,
        "allow_answer_modification": True,
        "shuffle_hanging_list": False,
        "allow_case_navigation": False,
        "access_request_handling": AccessRequestHandlingOptions.MANUAL_REVIEW,
        "roll_over_answers_for_n_cases": 0,
        "public": True,
        "description": "test description",
        "is_educational": False,
        "instant_verification": False,
    }

    if hanging_protocol_json:
        form_data["hanging_protocol"] = HangingProtocolFactory(
            json=hanging_protocol_json
        )

    form = ReaderStudyUpdateForm(
        user=creator,
        instance=object.base_object,
        data=form_data,
    )

    assert form.is_valid()

    view_content_example = form.generate_view_content_example()
    view_content_example_keys = (
        set(json.loads(view_content_example).keys())
        if view_content_example
        else None
    )
    assert view_content_example_keys == set(
        view_content_example_json_expected_keys
    )
