import tempfile
from pathlib import Path

import pytest
from actstream.actions import is_following
from bs4 import BeautifulSoup
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
    AlgorithmPermissionRequest,
    Job,
)
from grandchallenge.cases.widgets import ImageWidgetChoices
from grandchallenge.components.form_fields import (
    INTERFACE_FORM_FIELD_PREFIX,
    FileWidgetChoices,
)
from grandchallenge.components.models import (
    ComponentJob,
    ImportStatusChoices,
    InterfaceKindChoices,
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
            viewname="algorithms:custom-create",
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
    "socket_kwargs, content_parts",
    (
        (
            {
                "kind": InterfaceKindChoices.PANIMG_HEAT_MAP,
                "title": "some-overlay",
            },
            [
                '<select class="custom-select"',
                f'name="widget-choice-{INTERFACE_FORM_FIELD_PREFIX}some-overlay"',
            ],
        ),
        (
            {
                "kind": InterfaceKindChoices.PANIMG_IMAGE,
                "title": "some-medical-image",
            },
            [
                '<select class="custom-select"',
                f'name="widget-choice-{INTERFACE_FORM_FIELD_PREFIX}some-medical-image"',
            ],
        ),
        (
            {
                "kind": InterfaceKindChoices.BOOL,
                "title": "boolean",
            },
            [
                '<input type="checkbox"',
                f'name="{INTERFACE_FORM_FIELD_PREFIX}boolean"',
            ],
        ),
        (
            {
                "kind": InterfaceKindChoices.STRING,
                "title": "string",
            },
            [
                '<input type="text"',
                f'name="{INTERFACE_FORM_FIELD_PREFIX}string"',
            ],
        ),
        (
            {
                "kind": InterfaceKindChoices.INTEGER,
                "title": "integer",
            },
            [
                '<input type="number"',
                f'name="{INTERFACE_FORM_FIELD_PREFIX}integer"',
            ],
        ),
        (
            {
                "kind": InterfaceKindChoices.FLOAT,
                "title": "float",
            },
            [
                '<input type="number"',
                f'name="{INTERFACE_FORM_FIELD_PREFIX}float"',
                'step="any"',
            ],
        ),
        (
            {
                "kind": InterfaceKindChoices.TWO_D_BOUNDING_BOX,
                "title": "2d-bounding-box",
            },
            [
                'class="jsoneditorwidget ',
                f'<div id="jsoneditor_id_{INTERFACE_FORM_FIELD_PREFIX}2d-bounding-box"',
            ],
        ),
        (
            {
                "kind": InterfaceKindChoices.MULTIPLE_TWO_D_BOUNDING_BOXES,
                "title": "multiple-2d-bounding-boxes",
            },
            [
                'class="jsoneditorwidget ',
                f'<div id="jsoneditor_id_{INTERFACE_FORM_FIELD_PREFIX}multiple-2d-bounding-boxes"',
            ],
        ),
        (
            {
                "kind": InterfaceKindChoices.DISTANCE_MEASUREMENT,
                "title": "distance-measurement",
            },
            [
                'class="jsoneditorwidget ',
                f'<div id="jsoneditor_id_{INTERFACE_FORM_FIELD_PREFIX}distance-measurement"',
            ],
        ),
        (
            {
                "kind": InterfaceKindChoices.MULTIPLE_DISTANCE_MEASUREMENTS,
                "title": "multiple-distance-measurements",
            },
            [
                'class="jsoneditorwidget ',
                f'<div id="jsoneditor_id_{INTERFACE_FORM_FIELD_PREFIX}multiple-distance-measurements"',
            ],
        ),
        (
            {
                "kind": InterfaceKindChoices.POINT,
                "title": "point",
            },
            [
                'class="jsoneditorwidget ',
                f'<div id="jsoneditor_id_{INTERFACE_FORM_FIELD_PREFIX}point"',
            ],
        ),
        (
            {
                "kind": InterfaceKindChoices.MULTIPLE_POINTS,
                "title": "multiple-points",
            },
            [
                'class="jsoneditorwidget ',
                f'<div id="jsoneditor_id_{INTERFACE_FORM_FIELD_PREFIX}multiple-points"',
            ],
        ),
        (
            {
                "kind": InterfaceKindChoices.POLYGON,
                "title": "polygon",
            },
            [
                'class="jsoneditorwidget ',
                f'<div id="jsoneditor_id_{INTERFACE_FORM_FIELD_PREFIX}polygon"',
            ],
        ),
        (
            {
                "kind": InterfaceKindChoices.MULTIPLE_POLYGONS,
                "title": "multiple-polygons",
            },
            [
                'class="jsoneditorwidget ',
                f'<div id="jsoneditor_id_{INTERFACE_FORM_FIELD_PREFIX}multiple-polygons"',
            ],
        ),
        (
            {
                "kind": InterfaceKindChoices.ANY,
                "title": "anything",
                "store_in_database": False,
            },
            [
                '<select class="custom-select"',
                f'name="widget-choice-{INTERFACE_FORM_FIELD_PREFIX}anything"',
            ],
        ),
    ),
)
def test_create_job_input_fields(client, socket_kwargs, content_parts):
    alg, creator, _ = create_algorithm_with_input(**socket_kwargs)

    response = get_view_for_user(
        viewname="algorithms:job-create",
        client=client,
        reverse_kwargs={
            "slug": alg.slug,
            "interface_pk": alg.interfaces.first().pk,
        },
        follow=True,
        user=creator,
    )

    assert response.status_code == 200
    for c in content_parts:
        assert c in response.rendered_content


@pytest.mark.django_db
@pytest.mark.parametrize(
    "socket_kwargs",
    [
        {"kind": choice}
        for choice in set(InterfaceKindChoices).difference(
            {InterfaceKindChoices.BOOL, InterfaceKindChoices.ANY}
        )
    ]
    + [{"kind": InterfaceKindChoices.ANY, "store_in_database": False}],
)
def test_create_job_input_field_required_validation(client, socket_kwargs):
    alg, creator, input_socket = create_algorithm_with_input(**socket_kwargs)

    response = get_view_for_user(
        viewname="algorithms:job-create",
        client=client,
        reverse_kwargs={
            "slug": alg.slug,
            "interface_pk": alg.interfaces.first().pk,
        },
        method=client.post,
        follow=True,
        user=creator,
    )

    assert response.status_code == 200
    assert response.context["form"].errors == {
        f"{INTERFACE_FORM_FIELD_PREFIX}{input_socket.slug}": [
            "This field is required."
        ],
    }


def extract_form_data_from_response(response):
    html = response.content.decode()
    soup = BeautifulSoup(html, "html.parser")

    data = {}
    for tag in soup.find_all(["input", "select", "textarea"]):
        name = tag.get("name")
        if not name:
            continue

        if tag.name == "input":
            if tag.get("type") in ["checkbox", "radio"]:
                if tag.has_attr("checked"):
                    data[name] = tag.get("value", "on")
            else:
                data[name] = tag.get("value", "")
        elif tag.name == "select":
            selected = tag.find("option", selected=True)
            if selected:
                data[name] = selected.get("value")
            else:
                first = tag.find("option")
                if first:
                    data[name] = first.get("value")
        elif tag.name == "textarea":
            data[name] = tag.text

    return data


@pytest.mark.parametrize(
    "widget_choice",
    [
        ImageWidgetChoices.UNDEFINED,
        ImageWidgetChoices.IMAGE_SEARCH,
        ImageWidgetChoices.IMAGE_UPLOAD,
    ],
)
@pytest.mark.django_db
def test_create_job_image_kind_no_input_after_widget_choice_field_validation(
    client, widget_choice
):
    alg, creator, input_socket = create_algorithm_with_input(
        kind=InterfaceKindChoices.PANIMG_IMAGE
    )
    prefixed_interface_slug = (
        f"{INTERFACE_FORM_FIELD_PREFIX}{input_socket.slug}"
    )

    response = get_view_for_user(
        viewname="cases:select-image-widget",
        client=client,
        user=creator,
        data={
            f"widget-choice-{prefixed_interface_slug}": widget_choice.name,
            "prefixed-interface-slug": prefixed_interface_slug,
        },
    )
    data = extract_form_data_from_response(response)
    data[f"widget-choice-{prefixed_interface_slug}"] = widget_choice.name

    response = get_view_for_user(
        viewname="algorithms:job-create",
        client=client,
        reverse_kwargs={
            "slug": alg.slug,
            "interface_pk": alg.interfaces.first().pk,
        },
        method=client.post,
        data=data,
        follow=True,
        user=creator,
    )

    assert response.status_code == 200
    assert response.context["form"].errors == {
        f"{prefixed_interface_slug}": ["This field is required."],
    }


@pytest.mark.parametrize(
    "widget_choice",
    [
        FileWidgetChoices.UNDEFINED,
        FileWidgetChoices.FILE_SEARCH,
        FileWidgetChoices.FILE_UPLOAD,
    ],
)
@pytest.mark.django_db
def test_create_job_file_kind_no_input_after_widget_choice_field_validation(
    client, widget_choice
):
    alg, creator, input_socket = create_algorithm_with_input(
        kind=InterfaceKindChoices.PDF
    )
    prefixed_interface_slug = (
        f"{INTERFACE_FORM_FIELD_PREFIX}{input_socket.slug}"
    )

    response = get_view_for_user(
        viewname="components:select-file-widget",
        client=client,
        user=creator,
        data={
            f"widget-choice-{prefixed_interface_slug}": widget_choice.name,
            "prefixed-interface-slug": prefixed_interface_slug,
        },
    )
    data = extract_form_data_from_response(response)
    data[f"widget-choice-{prefixed_interface_slug}"] = widget_choice.name

    response = get_view_for_user(
        viewname="algorithms:job-create",
        client=client,
        reverse_kwargs={
            "slug": alg.slug,
            "interface_pk": alg.interfaces.first().pk,
        },
        method=client.post,
        data=data,
        follow=True,
        user=creator,
    )

    assert response.status_code == 200
    assert response.context["form"].errors == {
        f"{prefixed_interface_slug}": ["This field is required."],
    }


def create_algorithm_with_input(**kwargs):
    creator = get_algorithm_creator()
    VerificationFactory(user=creator, is_verified=True)
    alg = AlgorithmFactory()
    alg.add_editor(user=creator)
    input_socket = ComponentInterfaceFactory(**kwargs)
    interface = AlgorithmInterfaceFactory(
        inputs=[input_socket],
        outputs=[ComponentInterfaceFactory()],
    )
    alg.interfaces.add(interface)
    AlgorithmImageFactory(
        algorithm=alg,
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
    )
    return alg, creator, input_socket


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
        ci = ComponentInterfaceFactory(kind=InterfaceKindChoices.STRING)
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

    def test_form_invalid_with_too_many_jobs(self, settings):
        algorithm = AlgorithmFactory()
        user = UserFactory()
        AlgorithmImageFactory(
            algorithm=algorithm,
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
        )
        settings.ALGORITHMS_MAX_ACTIVE_JOBS_PER_USER = 1
        AlgorithmJobFactory(creator=user, time_limit=100)

        form = self.create_form(algorithm=algorithm, user=user)
        assert not form.is_valid()
        assert (
            "You have too many active jobs, please try again after they have completed"
            in str(form.errors["__all__"])
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
def test_cannot_activate_removed_image():
    alg = AlgorithmFactory()
    editor = UserFactory()
    alg.add_editor(editor)
    image = AlgorithmImageFactory(
        algorithm=alg, is_manifest_valid=True, is_desired_version=False
    )

    form = ImageActivateForm(
        user=editor, algorithm=alg, data={"algorithm_image": image}
    )

    assert form.is_valid()

    image.is_removed = True
    image.image.delete()

    form = ImageActivateForm(
        user=editor, algorithm=alg, data={"algorithm_image": image}
    )

    assert not form.is_valid()
    assert "This algorithm image has been removed" in str(
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

    with tempfile.NamedTemporaryFile(suffix=".tar.gz") as file:
        upload = create_upload_from_file(
            creator=user, file_path=Path(file.name)
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
            interface=algorithm.interfaces.first(),
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
            interface=algorithm.interfaces.first(),
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
            algorithm_interface=algorithm.interfaces.first(),
        )
        job.inputs.set(civs)

        form = JobCreateForm(
            algorithm=algorithm,
            user=editor,
            interface=algorithm.interfaces.first(),
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
def test_inputs_required_on_job_creation(algorithm_with_multiple_inputs):
    ci_json_in_db_without_schema = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.ANY,
        store_in_database=True,
    )
    interface = AlgorithmInterfaceFactory(
        inputs=[
            ci_json_in_db_without_schema,
            algorithm_with_multiple_inputs.ci_bool,
            algorithm_with_multiple_inputs.ci_str,
            algorithm_with_multiple_inputs.ci_json_in_db_with_schema,
            algorithm_with_multiple_inputs.ci_existing_img,
            algorithm_with_multiple_inputs.ci_json_file,
        ],
        outputs=[ComponentInterfaceFactory()],
    )
    algorithm_with_multiple_inputs.algorithm.interfaces.set([interface])

    form = JobCreateForm(
        algorithm=algorithm_with_multiple_inputs.algorithm,
        user=algorithm_with_multiple_inputs.editor,
        interface=interface,
        data={},
    )

    for name, field in form.fields.items():
        # boolean and json inputs that allow None should not be required,
        # all other inputs should be
        if name not in [
            "algorithm_model",
            "creator",
            f"{INTERFACE_FORM_FIELD_PREFIX}{algorithm_with_multiple_inputs.ci_bool.slug}",
            f"{INTERFACE_FORM_FIELD_PREFIX}{ci_json_in_db_without_schema.slug}",
        ]:
            assert field.required


@pytest.mark.django_db
def test_algorithm_form_gpu_limited_choices():
    form = AlgorithmForm(user=UserFactory())

    expected_choices = [
        GPUTypeChoices.NO_GPU,
        GPUTypeChoices.T4,
    ]

    actual_choices = form.fields["job_requires_gpu_type"].choices

    assert [c[0] for c in actual_choices] == expected_choices


@pytest.mark.django_db
def test_algorithm_form_gpu_choices_from_phases():
    user = UserFactory()
    algorithm = AlgorithmFactory()
    ci1, ci2, ci3, ci4, ci5, ci6 = ComponentInterfaceFactory.create_batch(6)
    inputs = [ci1, ci2]
    outputs = [ci3, ci4]
    interface = AlgorithmInterfaceFactory(inputs=inputs, outputs=outputs)
    algorithm.interfaces.set([interface])

    def assert_gpu_type_choices(expected_choices):
        form = AlgorithmForm(instance=algorithm, user=user)

        actual_choices = form.fields["job_requires_gpu_type"].choices

        assert [c[0] for c in actual_choices] == expected_choices

    assert_gpu_type_choices(
        [
            GPUTypeChoices.NO_GPU,
            GPUTypeChoices.T4,
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
        phase.algorithm_interfaces.set([interface])
        phase.challenge.add_participant(user)
        phases.append(phase)

    assert_gpu_type_choices(
        [
            GPUTypeChoices.NO_GPU,
            GPUTypeChoices.A100,
            GPUTypeChoices.A10G,
            GPUTypeChoices.V100,
            GPUTypeChoices.K80,
            GPUTypeChoices.T4,
        ]
    )

    phases[3].challenge.remove_participant(user)

    assert_gpu_type_choices(
        [
            GPUTypeChoices.NO_GPU,
            GPUTypeChoices.A100,
            GPUTypeChoices.A10G,
            GPUTypeChoices.V100,
            GPUTypeChoices.T4,
        ]
    )

    phases[2].submission_kind = SubmissionKindChoices.CSV
    phases[2].save()

    assert_gpu_type_choices(
        [
            GPUTypeChoices.NO_GPU,
            GPUTypeChoices.A100,
            GPUTypeChoices.A10G,
            GPUTypeChoices.T4,
        ]
    )

    phases[1].public = False
    phases[1].save()

    assert_gpu_type_choices(
        [
            GPUTypeChoices.NO_GPU,
            GPUTypeChoices.A100,
            GPUTypeChoices.T4,
        ]
    )

    interface2 = AlgorithmInterfaceFactory(inputs=[ci1, ci5], outputs=outputs)
    # add additional interface
    phases[0].algorithm_interfaces.add(interface2)

    assert_gpu_type_choices(
        [
            GPUTypeChoices.NO_GPU,
            GPUTypeChoices.T4,
        ]
    )

    # replace with different interface
    phases[0].algorithm_interfaces.set([interface2])

    assert_gpu_type_choices(
        [
            GPUTypeChoices.NO_GPU,
            GPUTypeChoices.T4,
        ]
    )

    phases[3].challenge.add_participant(user)

    assert_gpu_type_choices(
        [
            GPUTypeChoices.NO_GPU,
            GPUTypeChoices.K80,
            GPUTypeChoices.T4,
        ]
    )
    interface3 = AlgorithmInterfaceFactory(inputs=inputs, outputs=[ci4, ci6])
    phases[3].algorithm_interfaces.add(interface3)

    assert_gpu_type_choices(
        [
            GPUTypeChoices.NO_GPU,
            GPUTypeChoices.T4,
        ]
    )

    algorithm.interfaces.add(interface3)
    assert_gpu_type_choices(
        [
            GPUTypeChoices.NO_GPU,
            GPUTypeChoices.K80,
            GPUTypeChoices.T4,
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

        assert [c[0] for c in actual_choices] == expected_choices

    assert_gpu_type_choices(
        [
            GPUTypeChoices.NO_GPU,
            GPUTypeChoices.T4,
        ]
    )

    org1.add_member(user)

    assert_gpu_type_choices(
        [
            GPUTypeChoices.NO_GPU,
            GPUTypeChoices.A100,
            GPUTypeChoices.T4,
        ]
    )

    org2.add_member(user)

    assert_gpu_type_choices(
        [
            GPUTypeChoices.NO_GPU,
            GPUTypeChoices.A100,
            GPUTypeChoices.V100,
            GPUTypeChoices.T4,
        ]
    )


@pytest.mark.django_db
def test_algorithm_form_gpu_choices_from_organizations_and_phases():
    user = UserFactory()
    algorithm = AlgorithmFactory()
    ci1, ci2, ci3, ci4, ci5, ci6 = ComponentInterfaceFactory.create_batch(6)
    inputs = [ci1, ci2]
    outputs = [ci3, ci4]
    interface = AlgorithmInterfaceFactory(inputs=inputs, outputs=outputs)
    algorithm.interfaces.set([interface])

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

        assert [c[0] for c in actual_choices] == expected_choices

    assert_gpu_type_choices(
        [
            GPUTypeChoices.NO_GPU,
            GPUTypeChoices.T4,
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
        phase.algorithm_interfaces.set([interface])
        phase.challenge.add_participant(user)
        phases.append(phase)

    assert_gpu_type_choices(
        [
            GPUTypeChoices.NO_GPU,
            GPUTypeChoices.A10G,
            GPUTypeChoices.K80,
            GPUTypeChoices.T4,
        ]
    )

    org1.add_member(user)
    org2.add_member(user)

    assert_gpu_type_choices(
        [
            GPUTypeChoices.NO_GPU,
            GPUTypeChoices.A100,
            GPUTypeChoices.A10G,
            GPUTypeChoices.V100,
            GPUTypeChoices.K80,
            GPUTypeChoices.T4,
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
        interfaces=[AlgorithmInterfaceFactory.build()],
        structures=[],
        modalities=[],
        logo=ImageField(filename="test.jpeg"),
        phase=PhaseFactory.build(),
        user=UserFactory.build(),
    )

    expected_choices = [
        GPUTypeChoices.NO_GPU,
        GPUTypeChoices.T4,
    ]

    actual_choices = form.fields["job_requires_gpu_type"].choices

    assert [c[0] for c in actual_choices] == expected_choices


def test_algorithm_for_phase_form_gpu_additional_choices():
    form = AlgorithmForPhaseForm(
        workstation_config=WorkstationConfigFactory.build(),
        hanging_protocol=HangingProtocolFactory.build(),
        optional_hanging_protocols=[HangingProtocolFactory.build()],
        view_content="{}",
        display_editors=True,
        contact_email="test@test.com",
        workstation=WorkstationFactory.build(),
        interfaces=[AlgorithmInterfaceFactory.build()],
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
        GPUTypeChoices.NO_GPU,
        GPUTypeChoices.A100,
        GPUTypeChoices.T4,
    ]

    actual_choices = form.fields["job_requires_gpu_type"].choices

    assert [c[0] for c in actual_choices] == expected_choices


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
    interface = AlgorithmInterfaceFactory(inputs=inputs, outputs=outputs)
    algorithm.interfaces.set([interface])

    phases = []
    for max_memory in [42, 100, 200, 300, 400]:
        phase = PhaseFactory(
            submission_kind=SubmissionKindChoices.ALGORITHM,
            algorithm_maximum_settable_memory_gb=max_memory,
        )
        phase.algorithm_interfaces.set([interface])
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

    interface2 = AlgorithmInterfaceFactory(inputs=[ci1, ci5], outputs=outputs)
    phases[2].algorithm_interfaces.set([interface2])

    assert_max_value_validator(100)

    interface3 = AlgorithmInterfaceFactory(inputs=inputs, outputs=[ci4, ci6])
    phases[1].algorithm_interfaces.set([interface3])

    assert_max_value_validator(42)


@pytest.mark.django_db
def test_algorithm_form_max_memory_from_phases():
    user = UserFactory()
    algorithm = AlgorithmFactory()
    ci1, ci2, ci3, ci4, ci5, ci6 = ComponentInterfaceFactory.create_batch(6)
    inputs = [ci1, ci2]
    outputs = [ci3, ci4]
    interface = AlgorithmInterfaceFactory(inputs=inputs, outputs=outputs)
    algorithm.interfaces.set([interface])

    phases = []
    for max_memory in [42, 100, 200, 300, 400, 500]:
        phase = PhaseFactory(
            submission_kind=SubmissionKindChoices.ALGORITHM,
            algorithm_maximum_settable_memory_gb=max_memory,
        )
        phase.algorithm_interfaces.set([interface])
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

    interface2 = AlgorithmInterfaceFactory(inputs=[ci1, ci5], outputs=outputs)
    # adding an interface
    phases[2].algorithm_interfaces.add(interface2)
    assert_max_value_validator(100)
    # replacing the interface
    phases[2].algorithm_interfaces.set([interface2])
    assert_max_value_validator(100)

    interface3 = AlgorithmInterfaceFactory(inputs=inputs, outputs=[ci4, ci6])
    phases[1].algorithm_interfaces.set([interface3])

    assert_max_value_validator(42)

    # updating the algorithm's interface
    algorithm.interfaces.set([interface3])
    assert_max_value_validator(100)


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
    interface = AlgorithmInterfaceFactory(inputs=inputs, outputs=outputs)
    algorithm.interfaces.set([interface])
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
        phase.algorithm_interfaces.set([interface])
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
        interfaces=[AlgorithmInterfaceFactory.build()],
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
        base_obj=AlgorithmFactory(), data={"inputs": [ci], "outputs": [ci]}
    )
    assert form.is_valid() is False
    assert "The sets of Inputs and Outputs must be unique" in str(form.errors)


@pytest.mark.django_db
def test_algorithm_interface_unique_inputs_required():
    ci1, ci2 = ComponentInterfaceFactory.create_batch(2)
    alg = AlgorithmFactory()
    interface = AlgorithmInterfaceFactory(inputs=[ci1])
    alg.interfaces.add(interface)

    form = AlgorithmInterfaceForm(
        base_obj=alg, data={"inputs": [ci1], "outputs": [ci2]}
    )
    assert form.is_valid() is False
    assert (
        "An AlgorithmInterface for this algorithm with the same inputs already exists"
        in str(form.errors)
    )


def test_algorithm_for_phase_form_memory():
    form = AlgorithmForPhaseForm(
        workstation_config=WorkstationConfigFactory.build(),
        hanging_protocol=HangingProtocolFactory.build(),
        optional_hanging_protocols=[HangingProtocolFactory.build()],
        view_content="{}",
        display_editors=True,
        contact_email="test@test.com",
        workstation=WorkstationFactory.build(),
        interfaces=[AlgorithmInterfaceFactory.build()],
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
    def test_existing_io_is_reused(self):
        inp = ComponentInterfaceFactory()
        out = ComponentInterfaceFactory()
        io = AlgorithmInterfaceFactory()
        io.inputs.set([inp])
        io.outputs.set([out])

        alg = AlgorithmFactory()

        form = AlgorithmInterfaceForm(
            base_obj=alg,
            data={
                "inputs": [inp.pk],
                "outputs": [out.pk],
            },
        )
        assert form.is_valid()
        new_io = form.save()

        assert io == new_io
