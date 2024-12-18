from pathlib import Path

import pytest
from actstream.actions import is_following
from django.core.validators import MaxValueValidator, MinValueValidator
from factory.django import ImageField

from grandchallenge.algorithms.forms import (
    AlgorithmForm,
    AlgorithmForPhaseForm,
    AlgorithmInterfaceForm,
    AlgorithmModelForm,
    AlgorithmModelVersionControlForm,
    AlgorithmPublishForm,
    ImageActivateForm,
    JobCreateForm,
    JobForm,
)
from grandchallenge.algorithms.models import (
    Algorithm,
    AlgorithmAlgorithmInterface,
    AlgorithmPermissionRequest,
    Job,
)
from grandchallenge.components.form_fields import INTERFACE_FORM_FIELD_PREFIX
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentJob,
    ImportStatusChoices,
    InterfaceKind,
)
from grandchallenge.components.schemas import GPUTypeChoices
from grandchallenge.core.utils.access_requests import (
    AccessRequestHandlingOptions,
)
from grandchallenge.evaluation.utils import SubmissionKindChoices
from grandchallenge.verifications.models import Verification
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
    AlgorithmInterfaceFactory,
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
from tests.organizations_tests.factories import OrganizationFactory
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

    def try_create_algorithm():
        return get_view_for_user(
            viewname="algorithms:create",
            client=client,
            method=client.post,
            data={
                "title": "foo bar",
                "logo": uploaded_image(),
                "workstation": ws.pk,
                "interfaces": AlgorithmInterfaceFactory(),
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
        reverse_kwargs={
            "slug": alg.slug,
            "interface": alg.default_interface.pk,
        },
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
        reverse_kwargs={
            "slug": alg.slug,
            "interface": alg.default_interface.pk,
        },
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
        reverse_kwargs={
            "slug": alg.slug,
            "interface": alg.default_interface.pk,
        },
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
    interface = AlgorithmInterfaceFactory(
        inputs=[ComponentInterface.objects.get(slug=slug)],
        outputs=[ComponentInterfaceFactory()],
    )
    alg.interfaces.add(interface, through_defaults={"is_default": True})
    AlgorithmImageFactory(
        algorithm=alg,
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
    )
    return alg, creator


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

    def create_form(self, algorithm, user, algorithm_image=None):
        ci = ComponentInterfaceFactory(kind=ComponentInterface.Kind.STRING)
        interface = AlgorithmInterfaceFactory(inputs=[ci])
        algorithm.interfaces.add(interface)

        algorithm_image_kwargs = {}
        if algorithm_image:
            algorithm_image_kwargs = {
                "algorithm_image": str(algorithm_image.pk)
            }

        return JobCreateForm(
            algorithm=algorithm,
            user=user,
            interface=interface,
            data={
                **algorithm_image_kwargs,
                **get_interface_form_data(interface_slug=ci.slug, data="Foo"),
            },
        )

    def test_form_invalid_without_enough_credits(self, settings):
        algorithm = AlgorithmFactory(
            minimum_credits_per_job=(
                settings.ALGORITHMS_GENERAL_CREDITS_PER_MONTH_PER_USER + 1
            ),
        )
        user = UserFactory()
        AlgorithmImageFactory(
            algorithm=algorithm,
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
        )
        form = self.create_form(algorithm=algorithm, user=user)
        assert not form.is_valid()
        assert "You have run out of algorithm credits" in str(
            form.errors["__all__"]
        )

    def test_form_valid_for_editor(self, settings):
        algorithm = AlgorithmFactory(
            minimum_credits_per_job=(
                settings.ALGORITHMS_GENERAL_CREDITS_PER_MONTH_PER_USER + 1
            ),
        )
        algorithm_image = AlgorithmImageFactory(
            algorithm=algorithm,
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
        )
        user = UserFactory()

        algorithm.add_editor(user=user)

        form = self.create_form(
            algorithm=algorithm,
            user=user,
            algorithm_image=algorithm_image,
        )
        assert form.is_valid()

    def test_form_valid_with_credits(self):
        algorithm = AlgorithmFactory(minimum_credits_per_job=1)
        algorithm_image = AlgorithmImageFactory(
            algorithm=algorithm,
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
        )
        user = UserFactory()

        form = self.create_form(
            algorithm=algorithm,
            user=user,
            algorithm_image=algorithm_image,
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
        form = JobCreateForm(
            algorithm=algorithm,
            user=editor,
            interface=algorithm.default_interface,
            data={},
        )
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
        form = JobCreateForm(
            algorithm=algorithm,
            user=editor,
            interface=algorithm.default_interface,
            data={},
        )
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
            algorithm_interface=algorithm.default_interface,
        )
        job.inputs.set(civs)

        form = JobCreateForm(
            algorithm=algorithm,
            user=editor,
            interface=algorithm.default_interface,
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
    interface = AlgorithmInterfaceFactory(
        inputs=[ci_json_in_db_without_schema],
        outputs=[ComponentInterfaceFactory()],
    )
    algorithm_with_multiple_inputs.algorithm.interfaces.add(
        interface, through_defaults={"is_default": True}
    )

    form = JobCreateForm(
        algorithm=algorithm_with_multiple_inputs.algorithm,
        user=algorithm_with_multiple_inputs.editor,
        interface=interface,
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
    ci1, ci2, ci3, ci4, ci5, ci6 = ComponentInterfaceFactory.create_batch(6)
    inputs = [ci1, ci2]
    outputs = [ci3, ci4]
    algorithm.inputs.set(inputs)
    algorithm.outputs.set(outputs)

    def assert_gpu_type_choices(expected_choices):
        form = AlgorithmForm(instance=algorithm, user=user)

        actual_choices = form.fields["job_requires_gpu_type"].choices

        assert actual_choices == expected_choices

    assert_gpu_type_choices(
        [
            (GPUTypeChoices.NO_GPU, "No GPU"),
            (GPUTypeChoices.T4, "NVIDIA T4 Tensor Core GPU"),
        ]
    )

    phases = []
    for choice in [
        GPUTypeChoices.A100,
        GPUTypeChoices.A10G,
        GPUTypeChoices.V100,
        GPUTypeChoices.K80,
    ]:
        phase = PhaseFactory(
            submission_kind=SubmissionKindChoices.ALGORITHM,
            algorithm_selectable_gpu_type_choices=[
                GPUTypeChoices.NO_GPU,
                choice,
                GPUTypeChoices.T4,
            ],
        )
        phase.algorithm_inputs.set(inputs)
        phase.algorithm_outputs.set(outputs)
        phase.challenge.add_participant(user)
        phases.append(phase)

    assert_gpu_type_choices(
        [
            (GPUTypeChoices.NO_GPU, "No GPU"),
            (GPUTypeChoices.A100, "NVIDIA A100 Tensor Core GPU"),
            (GPUTypeChoices.A10G, "NVIDIA A10G Tensor Core GPU"),
            (GPUTypeChoices.V100, "NVIDIA V100 Tensor Core GPU"),
            (GPUTypeChoices.K80, "NVIDIA K80 GPU"),
            (GPUTypeChoices.T4, "NVIDIA T4 Tensor Core GPU"),
        ]
    )

    phases[3].challenge.remove_participant(user)

    assert_gpu_type_choices(
        [
            (GPUTypeChoices.NO_GPU, "No GPU"),
            (GPUTypeChoices.A100, "NVIDIA A100 Tensor Core GPU"),
            (GPUTypeChoices.A10G, "NVIDIA A10G Tensor Core GPU"),
            (GPUTypeChoices.V100, "NVIDIA V100 Tensor Core GPU"),
            (GPUTypeChoices.T4, "NVIDIA T4 Tensor Core GPU"),
        ]
    )

    phases[2].submission_kind = SubmissionKindChoices.CSV
    phases[2].save()

    assert_gpu_type_choices(
        [
            (GPUTypeChoices.NO_GPU, "No GPU"),
            (GPUTypeChoices.A100, "NVIDIA A100 Tensor Core GPU"),
            (GPUTypeChoices.A10G, "NVIDIA A10G Tensor Core GPU"),
            (GPUTypeChoices.T4, "NVIDIA T4 Tensor Core GPU"),
        ]
    )

    phases[1].public = False
    phases[1].save()

    assert_gpu_type_choices(
        [
            (GPUTypeChoices.NO_GPU, "No GPU"),
            (GPUTypeChoices.A100, "NVIDIA A100 Tensor Core GPU"),
            (GPUTypeChoices.T4, "NVIDIA T4 Tensor Core GPU"),
        ]
    )

    phases[0].algorithm_inputs.set([ci1, ci5])

    assert_gpu_type_choices(
        [
            (GPUTypeChoices.NO_GPU, "No GPU"),
            (GPUTypeChoices.T4, "NVIDIA T4 Tensor Core GPU"),
        ]
    )

    phases[3].challenge.add_participant(user)

    assert_gpu_type_choices(
        [
            (GPUTypeChoices.NO_GPU, "No GPU"),
            (GPUTypeChoices.K80, "NVIDIA K80 GPU"),
            (GPUTypeChoices.T4, "NVIDIA T4 Tensor Core GPU"),
        ]
    )

    phases[3].algorithm_outputs.set([ci4, ci6])

    assert_gpu_type_choices(
        [
            (GPUTypeChoices.NO_GPU, "No GPU"),
            (GPUTypeChoices.T4, "NVIDIA T4 Tensor Core GPU"),
        ]
    )


@pytest.mark.django_db
def test_algorithm_form_gpu_choices_from_organizations():
    user = UserFactory()
    org1 = OrganizationFactory(
        algorithm_selectable_gpu_type_choices=[
            GPUTypeChoices.NO_GPU,
            GPUTypeChoices.T4,
            GPUTypeChoices.A100,
        ],
    )
    org2 = OrganizationFactory(
        algorithm_selectable_gpu_type_choices=[
            GPUTypeChoices.NO_GPU,
            GPUTypeChoices.T4,
            GPUTypeChoices.V100,
        ],
    )

    def assert_gpu_type_choices(expected_choices):
        form = AlgorithmForm(user=user)

        actual_choices = form.fields["job_requires_gpu_type"].choices

        assert actual_choices == expected_choices

    assert_gpu_type_choices(
        [
            (GPUTypeChoices.NO_GPU, "No GPU"),
            (GPUTypeChoices.T4, "NVIDIA T4 Tensor Core GPU"),
        ]
    )

    org1.add_member(user)

    assert_gpu_type_choices(
        [
            (GPUTypeChoices.NO_GPU, "No GPU"),
            (GPUTypeChoices.A100, "NVIDIA A100 Tensor Core GPU"),
            (GPUTypeChoices.T4, "NVIDIA T4 Tensor Core GPU"),
        ]
    )

    org2.add_member(user)

    assert_gpu_type_choices(
        [
            (GPUTypeChoices.NO_GPU, "No GPU"),
            (GPUTypeChoices.A100, "NVIDIA A100 Tensor Core GPU"),
            (GPUTypeChoices.V100, "NVIDIA V100 Tensor Core GPU"),
            (GPUTypeChoices.T4, "NVIDIA T4 Tensor Core GPU"),
        ]
    )


@pytest.mark.django_db
def test_algorithm_form_gpu_choices_from_organizations_and_phases():
    user = UserFactory()
    algorithm = AlgorithmFactory()
    ci1, ci2, ci3, ci4, ci5, ci6 = ComponentInterfaceFactory.create_batch(6)
    inputs = [ci1, ci2]
    outputs = [ci3, ci4]
    algorithm.inputs.set(inputs)
    algorithm.outputs.set(outputs)
    org1 = OrganizationFactory(
        algorithm_selectable_gpu_type_choices=[
            GPUTypeChoices.NO_GPU,
            GPUTypeChoices.A100,
            GPUTypeChoices.T4,
        ],
    )
    org2 = OrganizationFactory(
        algorithm_selectable_gpu_type_choices=[
            GPUTypeChoices.NO_GPU,
            GPUTypeChoices.V100,
            GPUTypeChoices.T4,
        ],
    )

    def assert_gpu_type_choices(expected_choices):
        form = AlgorithmForm(instance=algorithm, user=user)

        actual_choices = form.fields["job_requires_gpu_type"].choices

        assert actual_choices == expected_choices

    assert_gpu_type_choices(
        [
            (GPUTypeChoices.NO_GPU, "No GPU"),
            (GPUTypeChoices.T4, "NVIDIA T4 Tensor Core GPU"),
        ]
    )

    phases = []
    for choice in [
        GPUTypeChoices.A10G,
        GPUTypeChoices.K80,
    ]:
        phase = PhaseFactory(
            submission_kind=SubmissionKindChoices.ALGORITHM,
            algorithm_selectable_gpu_type_choices=[
                GPUTypeChoices.NO_GPU,
                choice,
                GPUTypeChoices.T4,
            ],
        )
        phase.algorithm_inputs.set(inputs)
        phase.algorithm_outputs.set(outputs)
        phase.challenge.add_participant(user)
        phases.append(phase)

    assert_gpu_type_choices(
        [
            (GPUTypeChoices.NO_GPU, "No GPU"),
            (GPUTypeChoices.A10G, "NVIDIA A10G Tensor Core GPU"),
            (GPUTypeChoices.K80, "NVIDIA K80 GPU"),
            (GPUTypeChoices.T4, "NVIDIA T4 Tensor Core GPU"),
        ]
    )

    org1.add_member(user)
    org2.add_member(user)

    assert_gpu_type_choices(
        [
            (GPUTypeChoices.NO_GPU, "No GPU"),
            (GPUTypeChoices.A100, "NVIDIA A100 Tensor Core GPU"),
            (GPUTypeChoices.A10G, "NVIDIA A10G Tensor Core GPU"),
            (GPUTypeChoices.V100, "NVIDIA V100 Tensor Core GPU"),
            (GPUTypeChoices.K80, "NVIDIA K80 GPU"),
            (GPUTypeChoices.T4, "NVIDIA T4 Tensor Core GPU"),
        ]
    )


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
def test_algorithm_form_max_memory_from_phases_for_admins():
    user = UserFactory()
    algorithm = AlgorithmFactory()
    ci1, ci2, ci3, ci4, ci5, ci6 = ComponentInterfaceFactory.create_batch(6)
    inputs = [ci1, ci2]
    outputs = [ci3, ci4]
    algorithm.inputs.set(inputs)
    algorithm.outputs.set(outputs)
    phases = []
    for max_memory in [42, 100, 200, 300, 400]:
        phase = PhaseFactory(
            submission_kind=SubmissionKindChoices.ALGORITHM,
            algorithm_maximum_settable_memory_gb=max_memory,
        )
        phase.algorithm_inputs.set(inputs)
        phase.algorithm_outputs.set(outputs)
        phase.challenge.add_admin(user)
        phases.append(phase)

    def assert_max_value_validator(value):
        form = AlgorithmForm(instance=algorithm, user=user)

        validators = form.fields["job_requires_memory_gb"].validators

        max_validator = next(
            (v for v in validators if isinstance(v, MaxValueValidator)), None
        )
        assert max_validator is not None
        assert max_validator.limit_value == value

    assert_max_value_validator(400)

    phases[4].public = False
    phases[4].save()

    assert_max_value_validator(400)

    phases[4].challenge.remove_admin(user)

    assert_max_value_validator(300)

    phases[3].submission_kind = SubmissionKindChoices.CSV
    phases[3].save()

    assert_max_value_validator(200)

    phases[2].algorithm_inputs.set([ci1, ci5])

    assert_max_value_validator(100)

    phases[1].algorithm_outputs.set([ci4, ci6])

    assert_max_value_validator(42)


@pytest.mark.django_db
def test_algorithm_form_max_memory_from_phases():
    user = UserFactory()
    algorithm = AlgorithmFactory()
    ci1, ci2, ci3, ci4, ci5, ci6 = ComponentInterfaceFactory.create_batch(6)
    inputs = [ci1, ci2]
    outputs = [ci3, ci4]
    algorithm.inputs.set(inputs)
    algorithm.outputs.set(outputs)
    phases = []
    for max_memory in [42, 100, 200, 300, 400, 500]:
        phase = PhaseFactory(
            submission_kind=SubmissionKindChoices.ALGORITHM,
            algorithm_maximum_settable_memory_gb=max_memory,
        )
        phase.algorithm_inputs.set(inputs)
        phase.algorithm_outputs.set(outputs)
        phase.challenge.add_participant(user)
        phases.append(phase)

    def assert_max_value_validator(value):
        form = AlgorithmForm(instance=algorithm, user=user)

        validators = form.fields["job_requires_memory_gb"].validators

        max_validator = next(
            (v for v in validators if isinstance(v, MaxValueValidator)), None
        )
        assert max_validator is not None
        assert max_validator.limit_value == value

    assert_max_value_validator(500)

    phases[5].challenge.remove_participant(user)

    assert_max_value_validator(400)

    phases[4].submission_kind = SubmissionKindChoices.CSV
    phases[4].save()

    assert_max_value_validator(300)

    phases[3].public = False
    phases[3].save()

    assert_max_value_validator(200)

    phases[2].algorithm_inputs.set([ci1, ci5])

    assert_max_value_validator(100)

    phases[1].algorithm_outputs.set([ci4, ci6])

    assert_max_value_validator(42)


@pytest.mark.django_db
def test_algorithm_form_max_memory_from_organizations():
    user = UserFactory()
    org1 = OrganizationFactory(algorithm_maximum_settable_memory_gb=42)
    org2 = OrganizationFactory(algorithm_maximum_settable_memory_gb=1337)

    def assert_max_value_validator(value):
        form = AlgorithmForm(user=user)

        validators = form.fields["job_requires_memory_gb"].validators

        max_validator = next(
            (v for v in validators if isinstance(v, MaxValueValidator)), None
        )
        assert max_validator is not None
        assert max_validator.limit_value == value

    assert_max_value_validator(32)

    org1.add_member(user)

    assert_max_value_validator(42)

    org2.add_member(user)

    assert_max_value_validator(1337)


@pytest.mark.django_db
def test_algorithm_form_max_memory_from_organizations_and_phases():
    user = UserFactory()
    algorithm = AlgorithmFactory()
    ci1, ci2, ci3, ci4, ci5, ci6 = ComponentInterfaceFactory.create_batch(6)
    inputs = [ci1, ci2]
    outputs = [ci3, ci4]
    algorithm.inputs.set(inputs)
    algorithm.outputs.set(outputs)
    org1 = OrganizationFactory(algorithm_maximum_settable_memory_gb=42)
    org2 = OrganizationFactory(algorithm_maximum_settable_memory_gb=1337)

    def assert_max_value_validator(value):
        form = AlgorithmForm(instance=algorithm, user=user)

        validators = form.fields["job_requires_memory_gb"].validators

        max_validator = next(
            (v for v in validators if isinstance(v, MaxValueValidator)), None
        )
        assert max_validator is not None
        assert max_validator.limit_value == value

    assert_max_value_validator(32)

    for max_memory in [41, 42]:
        phase = PhaseFactory(
            submission_kind=SubmissionKindChoices.ALGORITHM,
            algorithm_maximum_settable_memory_gb=max_memory,
        )
        phase.algorithm_inputs.set(inputs)
        phase.algorithm_outputs.set(outputs)
        phase.challenge.add_participant(user)

    assert_max_value_validator(42)

    org1.add_member(user)
    org2.add_member(user)

    assert_max_value_validator(1337)


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


@pytest.mark.django_db
def test_algorithm_interface_disjoint_interfaces():
    ci = ComponentInterfaceFactory()
    form = AlgorithmInterfaceForm(
        algorithm=AlgorithmFactory(), data={"inputs": [ci], "outputs": [ci]}
    )
    assert form.is_valid() is False
    assert "The sets of Inputs and Outputs must be unique" in str(form.errors)


@pytest.mark.django_db
def test_algorithm_interface_default_interface_required():
    ci1, ci2 = ComponentInterfaceFactory.create_batch(2)
    alg = AlgorithmFactory()
    form = AlgorithmInterfaceForm(
        algorithm=alg,
        data={"inputs": [ci1], "outputs": [ci2], "set_as_default": False},
    )
    assert form.is_valid() is False
    assert "Your algorithm needs a default interface" in str(
        form.errors["set_as_default"]
    )

    alg.interfaces.add(
        AlgorithmInterfaceFactory(), through_defaults={"is_default": True}
    )
    del alg.default_interface
    form = AlgorithmInterfaceForm(
        algorithm=alg,
        data={"inputs": [ci1], "outputs": [ci2], "set_as_default": False},
    )
    assert form.is_valid()


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


class TestAlgorithmInterfaceForm:
    @pytest.mark.django_db
    def test_set_as_default_initial_value(self):
        alg = AlgorithmFactory()

        form = AlgorithmInterfaceForm(
            algorithm=alg,
        )
        assert form.fields["set_as_default"].initial

        alg.interfaces.add(
            AlgorithmInterfaceFactory(), through_defaults={"is_default": True}
        )

        del alg.default_interface

        form = AlgorithmInterfaceForm(
            algorithm=alg,
        )
        assert not form.fields["set_as_default"].initial

    @pytest.mark.django_db
    def test_existing_io_is_reused(self):
        inp = ComponentInterfaceFactory()
        out = ComponentInterfaceFactory()
        io = AlgorithmInterfaceFactory()
        io.inputs.set([inp])
        io.outputs.set([out])

        alg = AlgorithmFactory()

        form = AlgorithmInterfaceForm(
            algorithm=alg,
            data={
                "inputs": [inp.pk],
                "outputs": [out.pk],
                "set_as_default": True,
            },
        )
        assert form.is_valid()
        new_io = form.save()

        assert io == new_io

    @pytest.mark.django_db
    def test_new_default_interface_updates_related_interfaces(self):
        ci_1, ci_2 = ComponentInterfaceFactory.create_batch(2)
        alg = AlgorithmFactory()
        io = AlgorithmInterfaceFactory()
        alg.interfaces.add(io, through_defaults={"is_default": True})

        old_iot = AlgorithmAlgorithmInterface.objects.get()

        form = AlgorithmInterfaceForm(
            algorithm=alg,
            data={
                "inputs": [ci_1.pk],
                "outputs": [ci_2.pk],
                "set_as_default": True,
            },
        )
        form.is_valid()
        new_io = form.save()
        new_iot = AlgorithmAlgorithmInterface.objects.get(interface=new_io)
        old_iot.refresh_from_db()

        assert new_io != io
        assert new_iot.is_default
        assert not old_iot.is_default

    @pytest.mark.django_db
    def test_default_interface_for_algorithm_not_updated_when_adding_new_non_default_interface(
        self,
    ):
        alg = AlgorithmFactory()
        io = AlgorithmInterfaceFactory()
        alg.interfaces.add(io, through_defaults={"is_default": True})
        old_iot = AlgorithmAlgorithmInterface.objects.get()

        ci_1, ci_2 = ComponentInterfaceFactory.create_batch(2)

        form = AlgorithmInterfaceForm(
            algorithm=alg,
            data={
                "inputs": [ci_1.pk],
                "outputs": [ci_2.pk],
                "set_as_default": False,
            },
        )
        form.is_valid()
        new_io = form.save()
        old_iot.refresh_from_db()
        new_iot = AlgorithmAlgorithmInterface.objects.get(interface=new_io)

        assert new_io != io
        assert not new_iot.is_default
        assert old_iot.is_default

    @pytest.mark.django_db
    def test_is_default_is_updated_when_adding_an_already_existing_interface(
        self,
    ):
        alg = AlgorithmFactory()
        ci_1, ci_2 = ComponentInterfaceFactory.create_batch(2)

        io = AlgorithmInterfaceFactory()
        io.inputs.set([ci_1])
        io.outputs.set([ci_2])

        alg.interfaces.add(io, through_defaults={"is_default": True})
        old_iot = AlgorithmAlgorithmInterface.objects.get()

        form = AlgorithmInterfaceForm(
            algorithm=alg,
            data={
                "inputs": [ci_1.pk],
                "outputs": [ci_2.pk],
                "set_as_default": False,
            },
        )
        form.is_valid()
        new_io = form.save()
        old_iot.refresh_from_db()

        assert new_io == io
        assert not old_iot.is_default
