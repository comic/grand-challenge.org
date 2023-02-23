import pytest
from actstream.actions import is_following

from grandchallenge.algorithms.forms import (
    AlgorithmForm,
    AlgorithmPublishForm,
    JobCreateForm,
    JobForm,
)
from grandchallenge.algorithms.models import (
    Algorithm,
    AlgorithmPermissionRequest,
    Job,
)
from grandchallenge.components.models import ComponentInterface, ComponentJob
from grandchallenge.core.utils.access_requests import (
    AccessRequestHandlingOptions,
)
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
    AlgorithmJobFactory,
    AlgorithmPermissionRequestFactory,
)
from tests.algorithms_tests.utils import get_algorithm_creator
from tests.components_tests.factories import ComponentInterfaceFactory
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
                "image_requires_gpu": False,
                "image_requires_memory_gb": 4,
                "inputs": [ci.pk],
                "outputs": [ComponentInterfaceFactory().pk],
                "contact_email": creator.email,
                "display_editors": True,
                "access_request_handling": AccessRequestHandlingOptions.MANUAL_REVIEW,
                "view_content": "{}",
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
def test_algorithm_update_contains_repo_name(client, uploaded_image):
    # The algorithm creator should automatically get added to the editors group
    creator = get_algorithm_creator()
    VerificationFactory(user=creator, is_verified=True)

    response = get_view_for_user(
        viewname="algorithms:create",
        client=client,
        method=client.get,
        follow=True,
        user=creator,
    )

    assert response.status_code == 200
    assert "repo_name" not in response.rendered_content

    alg = AlgorithmFactory()
    alg.add_editor(user=creator)

    response = get_view_for_user(
        viewname="algorithms:update",
        client=client,
        method=client.get,
        reverse_kwargs={"slug": alg.slug},
        follow=True,
        user=creator,
    )

    assert response.status_code == 200
    assert "repo_name" in response.rendered_content


@pytest.mark.django_db
@pytest.mark.parametrize(
    "slug, content_parts",
    (
        (
            None,
            [
                '<select class="custom-select"',
                'name="WidgetChoice-generic-medical-image"',
            ],
        ),
        (
            "generic-overlay",
            [
                '<select class="custom-select"',
                'name="WidgetChoice-generic-overlay"',
            ],
        ),
        (
            "generic-medical-image",
            [
                '<select class="custom-select"',
                'name="WidgetChoice-generic-medical-image"',
            ],
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
        (
            "anything",
            [
                'class="user-upload"',
                '<div id="id_anything-drag-drop"',
            ],
        ),
    ),
)
def test_create_job_input_fields(
    client, component_interfaces, slug, content_parts
):
    alg, creator = create_algorithm_with_input(slug)

    response = get_view_for_user(
        viewname="algorithms:job-create",
        client=client,
        reverse_kwargs={"slug": alg.slug},
        follow=True,
        user=creator,
    )

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
def test_create_job_json_input_field_validation(
    client, component_interfaces, slug
):
    alg, creator = create_algorithm_with_input(slug)

    with pytest.raises(TypeError) as e:
        get_view_for_user(
            viewname="algorithms:job-create",
            client=client,
            reverse_kwargs={"slug": alg.slug},
            method=client.post,
            follow=True,
            user=creator,
        )
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
def test_create_job_simple_input_field_validation(
    client, component_interfaces, slug, content_parts
):
    alg, creator = create_algorithm_with_input(slug)

    response = get_view_for_user(
        viewname="algorithms:job-create",
        client=client,
        reverse_kwargs={"slug": alg.slug},
        method=client.post,
        follow=True,
        user=creator,
    )

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


@pytest.mark.django_db
def test_disjoint_interfaces():
    i = ComponentInterfaceFactory()
    form = AlgorithmForm(
        user=UserFactory(), data={"inputs": [i.pk], "outputs": [i.pk]}
    )
    assert form.is_valid() is False
    assert "The sets of Inputs and Outputs must be unique" in str(form.errors)


@pytest.mark.django_db
def test_publish_algorithm():
    algorithm = AlgorithmFactory()

    form = AlgorithmPublishForm(instance=algorithm, data={"public": True})
    assert form.is_valid() is False

    # add a summary and a mechanism
    algorithm.summary = "Summary"
    algorithm.mechanism = "Mechanism"
    algorithm.save()

    form = AlgorithmPublishForm(instance=algorithm, data={"public": True})
    assert form.is_valid() is False

    # set display editors to true
    algorithm.display_editors = True
    algorithm.save()
    form = AlgorithmPublishForm(instance=algorithm, data={"public": True})
    assert form.is_valid() is False

    # add contact email address
    algorithm.contact_email = "test@test.com"
    algorithm.save()
    form = AlgorithmPublishForm(instance=algorithm, data={"public": True})
    assert form.is_valid() is False

    # add a public result
    ai = AlgorithmImageFactory(
        algorithm=algorithm,
        is_manifest_valid=True,
        is_in_registry=True,
        is_on_sagemaker=True,
    )
    _ = AlgorithmJobFactory(
        algorithm_image=ai, status=Job.SUCCESS, public=True
    )
    del algorithm.latest_executable_image
    del algorithm.public_test_case
    form = AlgorithmPublishForm(instance=algorithm, data={"public": True})
    assert form.is_valid()


def test_only_publish_successful_jobs():
    job_success = AlgorithmJobFactory.build(status=ComponentJob.SUCCESS)
    job_failure = AlgorithmJobFactory.build(status=ComponentJob.FAILURE)

    form = JobForm(instance=job_failure, data={"public": True})
    assert not form.is_valid()

    form = JobForm(instance=job_success, data={"public": True})
    assert form.is_valid()


@pytest.mark.django_db
class TestJobCreateLimits:
    def test_form_invalid_without_enough_credits(self):
        algorithm = AlgorithmFactory(credits_per_job=100)
        algorithm.inputs.clear()
        user = UserFactory()

        user.user_credit.credits = 0
        user.user_credit.save()

        form = JobCreateForm(algorithm=algorithm, user=user, data={})

        assert not form.is_valid()
        assert form.errors == {
            "__all__": ["You have run out of algorithm credits"]
        }

    def test_form_valid_for_editor(self):
        algorithm = AlgorithmFactory(credits_per_job=100)
        algorithm.inputs.clear()
        user = UserFactory()

        user.user_credit.credits = 0
        user.user_credit.save()

        algorithm.add_editor(user=user)

        form = JobCreateForm(algorithm=algorithm, user=user, data={})

        assert form.is_valid()

    def test_form_valid_with_credits(self):
        algorithm = AlgorithmFactory(credits_per_job=1)
        algorithm.inputs.clear()
        user = UserFactory()

        form = JobCreateForm(algorithm=algorithm, user=user, data={})

        assert form.is_valid()
