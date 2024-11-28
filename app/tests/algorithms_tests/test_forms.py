from pathlib import Path

import pytest
from actstream.actions import is_following
from django.core.validators import MaxValueValidator, MinValueValidator
from factory.django import ImageField

from grandchallenge.algorithms.forms import (
    AlgorithmForm,
    AlgorithmForPhaseForm,
    AlgorithmModelForm,
    AlgorithmModelVersionControlForm,
    AlgorithmPublishForm,
    ImageActivateForm,
    JobCreateForm,
    JobForm,
)
from grandchallenge.algorithms.models import (
    Algorithm,
    AlgorithmPermissionRequest,
    Job,
)
from grandchallenge.components.form_fields import INTERFACE_FORM_FIELD_PREFIX
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentJob,
    GPUTypeChoices,
    ImportStatusChoices,
    InterfaceKind,
)
from grandchallenge.core.utils.access_requests import (
    AccessRequestHandlingOptions,
)
from grandchallenge.evaluation.utils import SubmissionKindChoices
from grandchallenge.verifications.models import Verification
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
    AlgorithmJobFactory,
    AlgorithmModelFactory,
    AlgorithmPermissionRequestFactory,
)
from tests.algorithms_tests.utils import get_algorithm_creator
from tests.components_tests.factories import ComponentInterfaceFactory
from tests.conftest import get_interface_form_data
from tests.evaluation_tests.factories import PhaseFactory
from tests.factories import (
    UserFactory,
    WorkstationConfigFactory,
    WorkstationFactory,
)
from tests.hanging_protocols_tests.factories import HangingProtocolFactory
from tests.uploads_tests.factories import (
    UserUploadFactory,
    create_upload_from_file,
)
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
                "inputs": [ci.pk],
                "outputs": [ComponentInterfaceFactory().pk],
                "minimum_credits_per_job": 20,
                "job_requires_gpu_type": GPUTypeChoices.NO_GPU,
                "job_requires_memory_gb": 4,
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
@pytest.mark.parametrize(
    "slug, content_parts",
    (
        (
            "generic-overlay",
            [
                '<select class="custom-select"',
                f'name="WidgetChoice-{INTERFACE_FORM_FIELD_PREFIX}generic-overlay"',
            ],
        ),
        (
            "generic-medical-image",
            [
                '<select class="custom-select"',
                f'name="WidgetChoice-{INTERFACE_FORM_FIELD_PREFIX}generic-medical-image"',
            ],
        ),
        (
            "boolean",
            [
                '<input type="checkbox"',
                f'name="{INTERFACE_FORM_FIELD_PREFIX}boolean"',
            ],
        ),
        (
            "string",
            [
                '<input type="text"',
                f'name="{INTERFACE_FORM_FIELD_PREFIX}string"',
            ],
        ),
        (
            "integer",
            [
                '<input type="number"',
                f'name="{INTERFACE_FORM_FIELD_PREFIX}integer"',
            ],
        ),
        (
            "float",
            [
                '<input type="number"',
                f'name="{INTERFACE_FORM_FIELD_PREFIX}float"',
                'step="any"',
            ],
        ),
        (
            "2d-bounding-box",
            [
                'class="jsoneditorwidget ',
                f'<div id="jsoneditor_id_{INTERFACE_FORM_FIELD_PREFIX}2d-bounding-box"',
            ],
        ),
        (
            "multiple-2d-bounding-boxes",
            [
                'class="jsoneditorwidget ',
                f'<div id="jsoneditor_id_{INTERFACE_FORM_FIELD_PREFIX}multiple-2d-bounding-boxes"',
            ],
        ),
        (
            "distance-measurement",
            [
                'class="jsoneditorwidget ',
                f'<div id="jsoneditor_id_{INTERFACE_FORM_FIELD_PREFIX}distance-measurement"',
            ],
        ),
        (
            "multiple-distance-measurements",
            [
                'class="jsoneditorwidget ',
                f'<div id="jsoneditor_id_{INTERFACE_FORM_FIELD_PREFIX}multiple-distance-measurements"',
            ],
        ),
        (
            "point",
            [
                'class="jsoneditorwidget ',
                f'<div id="jsoneditor_id_{INTERFACE_FORM_FIELD_PREFIX}point"',
            ],
        ),
        (
            "multiple-points",
            [
                'class="jsoneditorwidget ',
                f'<div id="jsoneditor_id_{INTERFACE_FORM_FIELD_PREFIX}multiple-points"',
            ],
        ),
        (
            "polygon",
            [
                'class="jsoneditorwidget ',
                f'<div id="jsoneditor_id_{INTERFACE_FORM_FIELD_PREFIX}polygon"',
            ],
        ),
        (
            "multiple-polygons",
            [
                'class="jsoneditorwidget ',
                f'<div id="jsoneditor_id_{INTERFACE_FORM_FIELD_PREFIX}multiple-polygons"',
            ],
        ),
        (
            "anything",
            [
                'class="user-upload"',
                f'<div id="X_id_{INTERFACE_FORM_FIELD_PREFIX}anything-drag-drop"',
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

    response = get_view_for_user(
        viewname="algorithms:job-create",
        client=client,
        reverse_kwargs={"slug": alg.slug},
        method=client.post,
        follow=True,
        user=creator,
    )
    assert response.context["form"].errors == {
        f"{INTERFACE_FORM_FIELD_PREFIX}{slug}": ["This field is required."],
    }


@pytest.mark.django_db
@pytest.mark.parametrize(
    "slug, content_parts",
    (
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
    VerificationFactory(user=creator, is_verified=True)
    alg = AlgorithmFactory()
    alg.add_editor(user=creator)
    alg.inputs.set([ComponentInterface.objects.get(slug=slug)])
    AlgorithmImageFactory(
        algorithm=alg,
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
    )
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

    # add a public result with inactive model
    ai = AlgorithmImageFactory(
        algorithm=algorithm,
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
    )
    am = AlgorithmModelFactory(
        algorithm=algorithm,
    )
    _ = AlgorithmJobFactory(
        algorithm_image=ai,
        algorithm_model=am,
        status=Job.SUCCESS,
        public=True,
        time_limit=algorithm.time_limit,
    )
    del algorithm.public_test_case
    del algorithm.active_image
    form = AlgorithmPublishForm(instance=algorithm, data={"public": True})
    assert not form.is_valid()

    # activating the model works
    am.is_desired_version = True
    am.save()
    del algorithm.public_test_case
    del algorithm.active_image
    del algorithm.active_model
    form = AlgorithmPublishForm(instance=algorithm, data={"public": True})
    assert form.is_valid()

    # deactivate model again, add public result without model
    am.is_desired_version = False
    am.save()
    _ = AlgorithmJobFactory(
        algorithm_image=ai,
        status=Job.SUCCESS,
        public=True,
        time_limit=algorithm.time_limit,
    )
    del algorithm.public_test_case
    del algorithm.active_image
    form = AlgorithmPublishForm(instance=algorithm, data={"public": True})
    assert form.is_valid()


def test_only_publish_successful_jobs():
    job_success = AlgorithmJobFactory.build(
        status=ComponentJob.SUCCESS, time_limit=60
    )
    job_failure = AlgorithmJobFactory.build(
        status=ComponentJob.FAILURE, time_limit=60
    )

    form = JobForm(instance=job_failure, data={"public": True})
    assert not form.is_valid()

    form = JobForm(instance=job_success, data={"public": True})
    assert form.is_valid()


@pytest.mark.django_db
class TestJobCreateLimits:
    def test_form_invalid_without_enough_credits(self, settings):
        algorithm = AlgorithmFactory(
            minimum_credits_per_job=(
                settings.ALGORITHMS_GENERAL_CREDITS_PER_MONTH_PER_USER + 1
            ),
        )
        algorithm.inputs.clear()
        user = UserFactory()
        AlgorithmImageFactory(
            algorithm=algorithm,
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
        )

        form = JobCreateForm(algorithm=algorithm, user=user, data={})

        assert not form.is_valid()
        assert form.errors == {
            "__all__": ["You have run out of algorithm credits"],
        }

    def test_form_valid_for_editor(self, settings):
        algorithm = AlgorithmFactory(
            minimum_credits_per_job=(
                settings.ALGORITHMS_GENERAL_CREDITS_PER_MONTH_PER_USER + 1
            ),
        )
        algorithm.inputs.clear()
        algorithm_image = AlgorithmImageFactory(
            algorithm=algorithm,
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
        )
        user = UserFactory()

        algorithm.add_editor(user=user)

        form = JobCreateForm(
            algorithm=algorithm,
            user=user,
            data={"algorithm_image": str(algorithm_image.pk)},
        )

        assert form.is_valid()

    def test_form_valid_with_credits(self):
        algorithm = AlgorithmFactory(minimum_credits_per_job=1)
        algorithm.inputs.clear()
        algorithm_image = AlgorithmImageFactory(
            algorithm=algorithm,
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
        )
        user = UserFactory()

        form = JobCreateForm(
            algorithm=algorithm,
            user=user,
            data={"algorithm_image": str(algorithm_image.pk)},
        )

        assert form.is_valid()


@pytest.mark.django_db
def test_image_activate_form():
    alg = AlgorithmFactory()
    editor = UserFactory()
    alg.add_editor(editor)
    i1 = AlgorithmImageFactory(
        algorithm=alg, is_manifest_valid=True, is_desired_version=False
    )
    i2 = AlgorithmImageFactory(
        algorithm=alg, is_manifest_valid=False, is_desired_version=False
    )
    i3 = AlgorithmImageFactory(
        algorithm=alg, is_manifest_valid=True, is_desired_version=True
    )

    form = ImageActivateForm(
        user=editor, algorithm=alg, data={"algorithm_image": i1}
    )
    assert i1 in form.fields["algorithm_image"].queryset
    assert i2 not in form.fields["algorithm_image"].queryset
    assert i3 not in form.fields["algorithm_image"].queryset
    assert form.is_valid()

    form = ImageActivateForm(
        user=editor, algorithm=alg, data={"algorithm_image": i2}
    )
    assert not form.is_valid()
    assert "Select a valid choice" in str(form.errors["algorithm_image"])

    i4 = AlgorithmImageFactory(
        algorithm=alg,
        is_manifest_valid=True,
        is_desired_version=False,
        import_status=ImportStatusChoices.STARTED,
    )
    form = ImageActivateForm(
        user=editor, algorithm=alg, data={"algorithm_image": i4}
    )
    assert not form.is_valid()
    assert "Image updating already in progress." in str(
        form.errors["algorithm_image"]
    )


@pytest.mark.django_db
def test_algorithm_model_form():
    user = UserFactory()
    alg = AlgorithmFactory()
    user_upload = UserUploadFactory(creator=user)
    user_upload.status = user_upload.StatusChoices.COMPLETED
    user_upload.save()

    form = AlgorithmModelForm(
        user=user,
        algorithm=alg,
        data={"user_upload": user_upload, "creator": user, "algorithm": alg},
    )
    assert not form.is_valid()
    assert "This upload is not a valid .tar.gz file" in str(form.errors)
    assert "Select a valid choice" in str(form.errors["creator"])

    Verification.objects.create(user=user, is_verified=True)
    upload = create_upload_from_file(
        creator=user,
        file_path=Path(__file__).parent / "resources" / "model.tar.gz",
    )
    AlgorithmModelFactory(creator=user)

    form2 = AlgorithmModelForm(
        user=user,
        algorithm=alg,
        data={"user_upload": upload, "creator": user, "algorithm": alg},
    )
    assert not form2.is_valid()
    assert (
        "You have an existing model importing, please wait for it to complete"
        in str(form2.errors)
    )


@pytest.mark.django_db
def test_model_version_control_form():
    alg = AlgorithmFactory()
    editor = UserFactory()
    alg.add_editor(editor)

    m1 = AlgorithmModelFactory(
        algorithm=alg,
        is_desired_version=False,
        import_status=ImportStatusChoices.COMPLETED,
    )
    m2 = AlgorithmModelFactory(
        algorithm=alg,
        is_desired_version=True,
        import_status=ImportStatusChoices.COMPLETED,
    )
    m3 = AlgorithmModelFactory(
        algorithm=alg,
        is_desired_version=False,
        import_status=ImportStatusChoices.FAILED,
    )
    m4 = AlgorithmModelFactory(
        algorithm=alg,
        is_desired_version=True,
        import_status=ImportStatusChoices.FAILED,
    )

    form = AlgorithmModelVersionControlForm(
        user=editor, algorithm=alg, activate=True
    )
    assert m1 in form.fields["algorithm_model"].queryset
    assert m2 not in form.fields["algorithm_model"].queryset
    assert m3 not in form.fields["algorithm_model"].queryset
    assert m4 not in form.fields["algorithm_model"].queryset

    form = AlgorithmModelVersionControlForm(
        user=editor, algorithm=alg, activate=False
    )
    assert m1 not in form.fields["algorithm_model"].queryset
    assert m2 in form.fields["algorithm_model"].queryset
    assert m3 not in form.fields["algorithm_model"].queryset
    assert m4 in form.fields["algorithm_model"].queryset

    AlgorithmModelFactory(
        algorithm=alg,
        is_desired_version=False,
    )
    form = AlgorithmModelVersionControlForm(
        user=editor, algorithm=alg, activate=True, data={"algorithm_model": m1}
    )
    assert not form.is_valid()
    assert "Model updating already in progress." in str(
        form.errors["algorithm_model"]
    )


@pytest.mark.django_db
class TestJobCreateForm:
    def test_creator_queryset(
        self, algorithm_with_image_and_model_and_two_inputs
    ):
        algorithm = algorithm_with_image_and_model_and_two_inputs.algorithm
        editor = algorithm.editors_group.user_set.first()
        form = JobCreateForm(algorithm=algorithm, user=editor, data={})
        assert list(form.fields["creator"].queryset.all()) == [editor]
        assert form.fields["creator"].initial == editor

    def test_algorithm_image_queryset(
        self, algorithm_with_image_and_model_and_two_inputs
    ):
        algorithm = algorithm_with_image_and_model_and_two_inputs.algorithm
        editor = algorithm.editors_group.user_set.first()
        # irrelevant Algorithm images
        inactive_image = AlgorithmImageFactory(algorithm=algorithm)
        image_for_different_alg = AlgorithmImageFactory(
            is_desired_version=True,
            is_manifest_valid=True,
            is_in_registry=True,
        )
        form = JobCreateForm(algorithm=algorithm, user=editor, data={})
        ai_qs = form.fields["algorithm_image"].queryset.all()
        assert algorithm.active_image in ai_qs
        assert inactive_image not in ai_qs
        assert image_for_different_alg not in ai_qs
        assert form.fields["algorithm_image"].initial == algorithm.active_image

    def test_cannot_create_job_with_same_inputs_twice(
        self, algorithm_with_image_and_model_and_two_inputs
    ):
        algorithm = algorithm_with_image_and_model_and_two_inputs.algorithm
        editor = algorithm.editors_group.user_set.first()

        civs = algorithm_with_image_and_model_and_two_inputs.civs
        job = AlgorithmJobFactory(
            algorithm_image=algorithm.active_image,
            algorithm_model=algorithm.active_model,
            status=Job.SUCCESS,
            time_limit=123,
        )
        job.inputs.set(civs)

        form = JobCreateForm(
            algorithm=algorithm,
            user=editor,
            data={
                "algorithm_image": algorithm.active_image,
                "algorithm_model": algorithm.active_model,
                **get_interface_form_data(
                    interface_slug=civs[0].interface.slug, data=civs[0].value
                ),
                **get_interface_form_data(
                    interface_slug=civs[1].interface.slug, data=civs[1].value
                ),
            },
        )
        assert not form.is_valid()
        assert (
            "A result for these inputs with the current image and model already exists."
            in str(form.errors)
        )


@pytest.mark.django_db
def test_all_inputs_required_on_job_creation(algorithm_with_multiple_inputs):
    ci_json_in_db_without_schema = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.ANY,
        store_in_database=True,
    )
    algorithm_with_multiple_inputs.algorithm.inputs.add(
        ci_json_in_db_without_schema
    )

    form = JobCreateForm(
        algorithm=algorithm_with_multiple_inputs.algorithm,
        user=algorithm_with_multiple_inputs.editor,
        data={},
    )

    for name, field in form.fields.items():
        if name not in ["algorithm_model", "creator"]:
            assert field.required


@pytest.mark.django_db
def test_algorithm_form_gpu_limited_choices():
    form = AlgorithmForm(user=UserFactory())

    expected_choices = [
        (GPUTypeChoices.NO_GPU, "No GPU"),
        (GPUTypeChoices.T4, "NVIDIA T4 Tensor Core GPU"),
    ]

    actual_choices = form.fields["job_requires_gpu_type"].choices

    assert actual_choices == expected_choices


@pytest.mark.django_db
def test_algorithm_form_gpu_choices_from_phases():
    user = UserFactory()
    algorithm = AlgorithmFactory()
    ci_in, ci_out = ComponentInterfaceFactory.create_batch(2)
    inputs = [ci_in]
    outputs = [ci_out]
    algorithm.inputs.set(inputs)
    algorithm.outputs.set(outputs)
    p1 = PhaseFactory(
        submission_kind=SubmissionKindChoices.ALGORITHM,
        algorithm_selectable_gpu_type_choices=[
            GPUTypeChoices.NO_GPU,
            GPUTypeChoices.T4,
            GPUTypeChoices.A100,
        ],
    )
    p1.algorithm_inputs.set(inputs)
    p1.algorithm_outputs.set(outputs)
    p1.challenge.participants_group.user_set.add(user)
    p2 = PhaseFactory(
        challenge=p1.challenge,
        submission_kind=SubmissionKindChoices.ALGORITHM,
        algorithm_selectable_gpu_type_choices=[
            GPUTypeChoices.NO_GPU,
            GPUTypeChoices.T4,
            GPUTypeChoices.K80,
        ],
    )
    p2.algorithm_inputs.set(inputs)
    p2.algorithm_outputs.set(outputs)
    p3 = PhaseFactory(  # excluded, wrong inputs
        challenge=p1.challenge,
        submission_kind=SubmissionKindChoices.ALGORITHM,
        algorithm_selectable_gpu_type_choices=[
            GPUTypeChoices.NO_GPU,
            GPUTypeChoices.T4,
            GPUTypeChoices.V100,
        ],
    )
    p3.algorithm_outputs.set(outputs)
    p4 = PhaseFactory(  # excluded, wrong outputs
        challenge=p1.challenge,
        submission_kind=SubmissionKindChoices.ALGORITHM,
        algorithm_selectable_gpu_type_choices=[
            GPUTypeChoices.NO_GPU,
            GPUTypeChoices.T4,
            GPUTypeChoices.V100,
        ],
    )
    p4.algorithm_inputs.set(inputs)
    PhaseFactory(  # excluded, not public
        challenge=p1.challenge,
        submission_kind=SubmissionKindChoices.ALGORITHM,
        algorithm_selectable_gpu_type_choices=[
            GPUTypeChoices.NO_GPU,
            GPUTypeChoices.T4,
            GPUTypeChoices.V100,
        ],
        public=False,
    )
    PhaseFactory(  # excluded, not algorithm submission kind
        challenge=p1.challenge,
        submission_kind=SubmissionKindChoices.CSV,
        algorithm_selectable_gpu_type_choices=[
            GPUTypeChoices.NO_GPU,
            GPUTypeChoices.T4,
            GPUTypeChoices.V100,
        ],
    )
    PhaseFactory(  # excluded, user not participant
        submission_kind=SubmissionKindChoices.ALGORITHM,
        algorithm_selectable_gpu_type_choices=[
            GPUTypeChoices.NO_GPU,
            GPUTypeChoices.T4,
            GPUTypeChoices.V100,
        ],
    )

    form = AlgorithmForm(instance=algorithm, user=user)

    expected_choices = [
        (GPUTypeChoices.NO_GPU, "No GPU"),
        (GPUTypeChoices.A100, "NVIDIA A100 Tensor Core GPU"),
        (GPUTypeChoices.K80, "NVIDIA K80 GPU"),
        (GPUTypeChoices.T4, "NVIDIA T4 Tensor Core GPU"),
    ]

    actual_choices = form.fields["job_requires_gpu_type"].choices

    assert actual_choices == expected_choices


def test_algorithm_for_phase_form_gpu_limited_choices():
    form = AlgorithmForPhaseForm(
        workstation_config=WorkstationConfigFactory.build(),
        hanging_protocol=HangingProtocolFactory.build(),
        optional_hanging_protocols=[HangingProtocolFactory.build()],
        view_content="{}",
        display_editors=True,
        contact_email="test@test.com",
        workstation=WorkstationFactory.build(),
        inputs=[ComponentInterfaceFactory.build()],
        outputs=[ComponentInterfaceFactory.build()],
        structures=[],
        modalities=[],
        logo=ImageField(filename="test.jpeg"),
        phase=PhaseFactory.build(),
        user=UserFactory.build(),
    )

    expected_choices = [
        (GPUTypeChoices.NO_GPU, "No GPU"),
        (GPUTypeChoices.T4, "NVIDIA T4 Tensor Core GPU"),
    ]

    actual_choices = form.fields["job_requires_gpu_type"].choices

    assert actual_choices == expected_choices


def test_algorithm_for_phase_form_gpu_additional_choices():
    form = AlgorithmForPhaseForm(
        workstation_config=WorkstationConfigFactory.build(),
        hanging_protocol=HangingProtocolFactory.build(),
        optional_hanging_protocols=[HangingProtocolFactory.build()],
        view_content="{}",
        display_editors=True,
        contact_email="test@test.com",
        workstation=WorkstationFactory.build(),
        inputs=[ComponentInterfaceFactory.build()],
        outputs=[ComponentInterfaceFactory.build()],
        structures=[],
        modalities=[],
        logo=ImageField(filename="test.jpeg"),
        phase=PhaseFactory.build(
            algorithm_selectable_gpu_type_choices=[
                GPUTypeChoices.NO_GPU,
                GPUTypeChoices.T4,
                GPUTypeChoices.A100,
            ]
        ),
        user=UserFactory.build(),
    )

    expected_choices = [
        (GPUTypeChoices.NO_GPU, "No GPU"),
        (GPUTypeChoices.A100, "NVIDIA A100 Tensor Core GPU"),
        (GPUTypeChoices.T4, "NVIDIA T4 Tensor Core GPU"),
    ]

    actual_choices = form.fields["job_requires_gpu_type"].choices

    assert actual_choices == expected_choices


@pytest.mark.django_db
def test_algorithm_form_memory_limited():
    form = AlgorithmForm(user=UserFactory())

    validators = form.fields["job_requires_memory_gb"].validators

    min_validator = next(
        (v for v in validators if isinstance(v, MinValueValidator)), None
    )
    assert min_validator is not None
    assert min_validator.limit_value == 4

    max_validator = next(
        (v for v in validators if isinstance(v, MaxValueValidator)), None
    )
    assert max_validator is not None
    assert max_validator.limit_value == 32


@pytest.mark.django_db
def test_algorithm_form_max_memory_from_phases():
    user = UserFactory()
    algorithm = AlgorithmFactory()
    ci_in, ci_out = ComponentInterfaceFactory.create_batch(2)
    inputs = [ci_in]
    outputs = [ci_out]
    algorithm.inputs.set(inputs)
    algorithm.outputs.set(outputs)
    p1 = PhaseFactory(
        submission_kind=SubmissionKindChoices.ALGORITHM,
        algorithm_maximum_settable_memory_gb=21,
    )
    p1.algorithm_inputs.set(inputs)
    p1.algorithm_outputs.set(outputs)
    p1.challenge.participants_group.user_set.add(user)
    p2 = PhaseFactory(
        challenge=p1.challenge,
        submission_kind=SubmissionKindChoices.ALGORITHM,
        algorithm_maximum_settable_memory_gb=42,
    )
    p2.algorithm_inputs.set(inputs)
    p2.algorithm_outputs.set(outputs)
    p3 = PhaseFactory(  # excluded, wrong inputs
        challenge=p1.challenge,
        submission_kind=SubmissionKindChoices.ALGORITHM,
        algorithm_maximum_settable_memory_gb=1337,
    )
    p3.algorithm_outputs.set(outputs)
    p4 = PhaseFactory(  # excluded, wrong outputs
        challenge=p1.challenge,
        submission_kind=SubmissionKindChoices.ALGORITHM,
        algorithm_maximum_settable_memory_gb=1337,
    )
    p4.algorithm_inputs.set(inputs)
    PhaseFactory(  # excluded, not public
        challenge=p1.challenge,
        submission_kind=SubmissionKindChoices.ALGORITHM,
        algorithm_maximum_settable_memory_gb=1337,
        public=False,
    )
    PhaseFactory(  # excluded, not algorithm submission kind
        challenge=p1.challenge,
        submission_kind=SubmissionKindChoices.CSV,
        algorithm_maximum_settable_memory_gb=1337,
    )
    PhaseFactory(  # excluded, user not participant
        submission_kind=SubmissionKindChoices.ALGORITHM,
        algorithm_maximum_settable_memory_gb=1337,
    )

    form = AlgorithmForm(instance=algorithm, user=user)

    validators = form.fields["job_requires_memory_gb"].validators

    max_validator = next(
        (v for v in validators if isinstance(v, MaxValueValidator)), None
    )
    assert max_validator is not None
    assert max_validator.limit_value == 42


def test_algorithm_for_phase_form_memory_limited():
    form = AlgorithmForPhaseForm(
        workstation_config=WorkstationConfigFactory.build(),
        hanging_protocol=HangingProtocolFactory.build(),
        optional_hanging_protocols=[HangingProtocolFactory.build()],
        view_content="{}",
        display_editors=True,
        contact_email="test@test.com",
        workstation=WorkstationFactory.build(),
        inputs=[ComponentInterfaceFactory.build()],
        outputs=[ComponentInterfaceFactory.build()],
        structures=[],
        modalities=[],
        logo=ImageField(filename="test.jpeg"),
        phase=PhaseFactory.build(),
        user=UserFactory.build(),
    )

    validators = form.fields["job_requires_memory_gb"].validators

    min_validator = next(
        (v for v in validators if isinstance(v, MinValueValidator)), None
    )
    assert min_validator is not None
    assert min_validator.limit_value == 4

    max_validator = next(
        (v for v in validators if isinstance(v, MaxValueValidator)), None
    )
    assert max_validator is not None
    assert max_validator.limit_value == 32


def test_algorithm_for_phase_form_memory():
    form = AlgorithmForPhaseForm(
        workstation_config=WorkstationConfigFactory.build(),
        hanging_protocol=HangingProtocolFactory.build(),
        optional_hanging_protocols=[HangingProtocolFactory.build()],
        view_content="{}",
        display_editors=True,
        contact_email="test@test.com",
        workstation=WorkstationFactory.build(),
        inputs=[ComponentInterfaceFactory.build()],
        outputs=[ComponentInterfaceFactory.build()],
        structures=[],
        modalities=[],
        logo=ImageField(filename="test.jpeg"),
        phase=PhaseFactory.build(algorithm_maximum_settable_memory_gb=42),
        user=UserFactory.build(),
    )

    validators = form.fields["job_requires_memory_gb"].validators

    max_validator = next(
        (v for v in validators if isinstance(v, MaxValueValidator)), None
    )
    assert max_validator is not None
    assert max_validator.limit_value == 42
