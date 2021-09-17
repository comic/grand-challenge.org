import pytest
from actstream.actions import is_following

from grandchallenge.algorithms.models import (
    Algorithm,
    AlgorithmPermissionRequest,
)
from grandchallenge.components.models import ComponentInterface
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmPermissionRequestFactory,
)
from tests.algorithms_tests.utils import get_algorithm_creator
from tests.factories import UserFactory, WorkstationFactory
from tests.utils import get_view_for_user
from tests.verification_tests.factories import VerificationFactory


@pytest.mark.django_db
def test_editor_update_form(client):
    alg, _ = AlgorithmFactory(), AlgorithmFactory()

    editor = UserFactory()
    alg.editors_group.user_set.add(editor)

    assert alg.editors_group.user_set.count() == 1

    new_editor = UserFactory()
    assert not alg.is_editor(user=new_editor)
    response = get_view_for_user(
        viewname="algorithms:editors-update",
        client=client,
        method=client.post,
        data={"user": new_editor.pk, "action": "ADD"},
        reverse_kwargs={"slug": alg.slug},
        follow=True,
        user=editor,
    )
    assert response.status_code == 200

    alg.refresh_from_db()
    assert alg.editors_group.user_set.count() == 2
    assert alg.is_editor(user=new_editor)

    response = get_view_for_user(
        viewname="algorithms:editors-update",
        client=client,
        method=client.post,
        data={"user": new_editor.pk, "action": "REMOVE"},
        reverse_kwargs={"slug": alg.slug},
        follow=True,
        user=editor,
    )
    assert response.status_code == 200

    alg.refresh_from_db()
    assert alg.editors_group.user_set.count() == 1
    assert not alg.is_editor(user=new_editor)


@pytest.mark.django_db
def test_user_update_form(client):
    alg, _ = AlgorithmFactory(), AlgorithmFactory()

    editor = UserFactory()
    alg.editors_group.user_set.add(editor)

    assert alg.users_group.user_set.count() == 0

    new_user = UserFactory()
    pr = AlgorithmPermissionRequestFactory(user=new_user, algorithm=alg)

    assert not alg.is_user(user=new_user)
    assert pr.status == AlgorithmPermissionRequest.PENDING
    response = get_view_for_user(
        viewname="algorithms:users-update",
        client=client,
        method=client.post,
        data={"user": new_user.pk, "action": "ADD"},
        reverse_kwargs={"slug": alg.slug},
        follow=True,
        user=editor,
    )
    assert response.status_code == 200

    alg.refresh_from_db()
    pr.refresh_from_db()
    assert alg.users_group.user_set.count() == 1
    assert alg.is_user(user=new_user)
    assert pr.status == AlgorithmPermissionRequest.ACCEPTED

    response = get_view_for_user(
        viewname="algorithms:users-update",
        client=client,
        method=client.post,
        data={"user": new_user.pk, "action": "REMOVE"},
        reverse_kwargs={"slug": alg.slug},
        follow=True,
        user=editor,
    )
    assert response.status_code == 200

    alg.refresh_from_db()
    pr.refresh_from_db()
    assert alg.users_group.user_set.count() == 0
    assert not alg.is_user(user=new_user)
    assert pr.status == AlgorithmPermissionRequest.REJECTED


@pytest.mark.django_db
def test_algorithm_create(client, uploaded_image):
    # The algorithm creator should automatically get added to the editors group
    creator = get_algorithm_creator()
    VerificationFactory(user=creator, is_verified=True)

    ws = WorkstationFactory()
    ci = ComponentInterface.objects.get(slug="generic-medical-image")

    def try_create_algorithm():
        return get_view_for_user(
            viewname="algorithms:create",
            client=client,
            method=client.post,
            data={
                "title": "foo bar",
                "logo": uploaded_image(),
                "workstation": ws.pk,
                "credits_per_job": 1,
                "image_requires_gpu": False,
                "image_requires_memory_gb": 4,
                "inputs": [ci.pk],
                "outputs": [ci.pk],
            },
            follow=True,
            user=creator,
        )

    response = try_create_algorithm()
    assert "error_1_id_workstation" in response.rendered_content

    # The editor must have view permissions for the workstation to add it
    ws.add_user(user=creator)

    response = try_create_algorithm()
    assert "error_1_id_workstation" not in response.rendered_content
    assert response.status_code == 200

    alg = Algorithm.objects.get(title="foo bar")

    assert alg.slug == "foo-bar"
    assert alg.is_editor(user=creator)
    assert not alg.is_user(user=creator)
    assert is_following(user=creator, obj=alg)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "slug, content_parts",
    (
        (None, ['<input type="file"', '<input name="generic-medical-image"']),
        (
            "generic-overlay",
            ['<input type="file"', '<input name="generic-overlay"'],
        ),
        (
            "generic-medical-image",
            ['<input type="file"', '<input name="generic-medical-image"'],
        ),
        ("boolean", ['<input type="checkbox"', 'name="boolean"']),
        ("string", ['<input type="text" name="string"']),
        ("integer", ['<input type="number"', 'name="integer"']),
        ("float", ['<input type="number"', 'name="float"', 'step="any"']),
        (
            "2d-bounding-box",
            [
                'class="jsoneditorwidget ',
                '<div id="jsoneditor_id_2d-bounding-box"',
            ],
        ),
        (
            "multiple-2d-bounding-boxes",
            [
                'class="jsoneditorwidget ',
                '<div id="jsoneditor_id_multiple-2d-bounding-boxes"',
            ],
        ),
        (
            "distance-measurement",
            [
                'class="jsoneditorwidget ',
                '<div id="jsoneditor_id_distance-measurement"',
            ],
        ),
        (
            "multiple-distance-measurements",
            [
                'class="jsoneditorwidget ',
                '<div id="jsoneditor_id_multiple-distance-measurements"',
            ],
        ),
        (
            "point",
            ['class="jsoneditorwidget ', '<div id="jsoneditor_id_point"'],
        ),
        (
            "multiple-points",
            [
                'class="jsoneditorwidget ',
                '<div id="jsoneditor_id_multiple-points"',
            ],
        ),
        (
            "polygon",
            ['class="jsoneditorwidget ', '<div id="jsoneditor_id_polygon"'],
        ),
        (
            "multiple-polygons",
            [
                'class="jsoneditorwidget ',
                '<div id="jsoneditor_id_multiple-polygons"',
            ],
        ),
    ),
)
def test_create_experiment_input_fields(
    client, component_interfaces, slug, content_parts
):
    alg, creator = create_algorithm_with_input(slug)

    def load_create_experiment_form():
        return get_view_for_user(
            viewname="algorithms:execution-session-create-new",
            client=client,
            reverse_kwargs={"slug": alg.slug},
            follow=True,
            user=creator,
        )

    response = load_create_experiment_form()
    assert response.status_code == 200
    for c in content_parts:
        assert c in response.rendered_content


@pytest.mark.django_db
@pytest.mark.parametrize(
    "slug",
    [
        "2d-bounding-box",
        "multiple-2d-bounding-boxes",
        "distance-measurement",
        "multiple-distance-measurements",
        "point",
        "multiple-points",
        "polygon",
        "multiple-polygons",
    ],
)
def test_create_experiment_json_input_field_validation(
    client, component_interfaces, slug
):
    alg, creator = create_algorithm_with_input(slug)

    def try_create_algorithm_experiment():
        return get_view_for_user(
            viewname="algorithms:execution-session-create-new",
            client=client,
            reverse_kwargs={"slug": alg.slug},
            method=client.post,
            follow=True,
            user=creator,
        )

    with pytest.raises(TypeError) as e:
        try_create_algorithm_experiment()
    assert (
        "the JSON object must be str, bytes or bytearray, not NoneType"
        in str(e)
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "slug, content_parts",
    (
        (None, ['class="invalid-feedback"', "This field is required."]),
        (
            "generic-overlay",
            ['class="invalid-feedback"', "This field is required."],
        ),
        ("string", ['class="invalid-feedback"', "This field is required."]),
        ("integer", ['class="invalid-feedback"', "This field is required."]),
        ("float", ['class="invalid-feedback"', "This field is required."]),
    ),
)
def test_create_experiment_simple_input_field_validation(
    client, component_interfaces, slug, content_parts
):
    alg, creator = create_algorithm_with_input(slug)

    def try_create_algorithm_experiment():
        return get_view_for_user(
            viewname="algorithms:execution-session-create-new",
            client=client,
            reverse_kwargs={"slug": alg.slug},
            method=client.post,
            follow=True,
            user=creator,
        )

    response = try_create_algorithm_experiment()
    assert response.status_code == 200
    for c in content_parts:
        assert c in response.rendered_content


def create_algorithm_with_input(slug):
    creator = get_algorithm_creator()
    alg = AlgorithmFactory()
    alg.add_editor(user=creator)
    if slug:
        alg.inputs.set([ComponentInterface.objects.get(slug=slug)])
    return alg, creator
