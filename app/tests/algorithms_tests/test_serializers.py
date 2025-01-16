import pytest
from guardian.shortcuts import assign_perm
from rest_framework.exceptions import ErrorDetail

from grandchallenge.algorithms.models import Job
from grandchallenge.algorithms.serializers import (
    HyperlinkedJobSerializer,
    JobPostSerializer,
)
from grandchallenge.cases.models import RawImageUploadSession
from grandchallenge.components.models import ComponentInterface
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
    AlgorithmJobFactory,
)
from tests.cases_tests.factories import RawImageUploadSessionFactory
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.factories import ImageFactory, UserFactory
from tests.uploads_tests.factories import UserUploadFactory


@pytest.mark.django_db
def test_algorithm_relations_on_job_serializer(rf):
    job = AlgorithmJobFactory(time_limit=60)
    serializer = HyperlinkedJobSerializer(
        job, context={"request": rf.get("/foo", secure=True)}
    )
    assert serializer.data["algorithm_image"] == job.algorithm_image.api_url
    assert (
        serializer.data["algorithm"] == job.algorithm_image.algorithm.api_url
    )


@pytest.mark.xfail(reason="Still to be addressed for optional inputs pitch")
@pytest.mark.django_db
@pytest.mark.parametrize(
    "title, "
    "add_user, "
    "image_ready, "
    "algorithm_interface_titles, "
    "job_interface_slugs, "
    "error_message, "
    "existing_jobs",
    (
        (
            "algorithm1",
            False,
            False,
            ("TestInterface 1",),
            ("testinterface-1",),
            "Invalid hyperlink - Object does not exist",
            False,
        ),
        (
            "algorithm1",
            True,
            False,
            ("TestInterface 1",),
            ("testinterface-1",),
            "Algorithm image is not ready to be used",
            False,
        ),
        (
            "algorithm1",
            True,
            True,
            ("TestInterface 1",),
            ("testinterface-3",),
            "Object with slug=testinterface-3 does not exist.",
            False,
        ),
        (
            "algorithm1",
            True,
            True,
            ("TestInterface 1", "TestInterface 2"),
            ("testinterface-1",),
            "Interface(s) TestInterface 2 do not have a default value and should be provided.",
            False,
        ),
        (
            "algorithm1",
            True,
            True,
            ("TestInterface 1",),
            ("testinterface-1", "testinterface-2"),
            "Provided inputs(s) TestInterface 2 are not defined for this algorithm",
            False,
        ),
        (
            "algorithm1",
            True,
            True,
            ("TestInterface 1", "TestInterface 2"),
            ("testinterface-1", "testinterface-2"),
            "A result for these inputs with the current image and model already exists.",
            True,
        ),
        (
            "algorithm1",
            True,
            True,
            ("TestInterface 1", "TestInterface 2"),
            ("testinterface-1", "testinterface-2"),
            None,
            False,
        ),
    ),
)
def test_algorithm_job_post_serializer_validations(
    title,
    add_user,
    image_ready,
    algorithm_interface_titles,
    job_interface_slugs,
    error_message,
    existing_jobs,
    rf,
):
    # setup
    user = UserFactory()
    interfaces = {
        "TestInterface 1": ComponentInterfaceFactory(
            kind=ComponentInterface.Kind.STRING, title="TestInterface 1"
        ),
        "TestInterface 2": ComponentInterfaceFactory(
            kind=ComponentInterface.Kind.STRING, title="TestInterface 2"
        ),
    }
    algorithm_image = AlgorithmImageFactory(
        is_manifest_valid=image_ready,
        is_in_registry=image_ready,
        is_desired_version=image_ready,
    )
    algorithm_image.algorithm.title = title
    algorithm_image.algorithm.inputs.set(
        [interfaces[title] for title in algorithm_interface_titles]
    )
    if add_user:
        algorithm_image.algorithm.add_user(user)

    algorithm_image.algorithm.save()

    if existing_jobs:
        civs = []
        for _, interface in interfaces.items():
            civs.append(
                ComponentInterfaceValueFactory(
                    interface=interface, value="dummy"
                )
            )
        existing_job = AlgorithmJobFactory(
            algorithm_image=algorithm_image, status=Job.SUCCESS, time_limit=10
        )
        existing_job.inputs.set(civs)

    job = {
        "algorithm": algorithm_image.algorithm.api_url,
        "inputs": [
            {"interface": interface, "value": "dummy"}
            for interface in job_interface_slugs
        ],
    }

    # test
    request = rf.get("/foo")
    request.user = user
    serializer = JobPostSerializer(data=job, context={"request": request})

    # verify
    assert serializer.is_valid() == (error_message is None)
    if error_message:
        assert error_message in str(serializer.errors)
    else:
        assert len(Job.objects.all()) == 0
        serializer.create(serializer.validated_data)
        assert len(Job.objects.all()) == 1
        job = Job.objects.first()
        assert job.status == job.VALIDATING_INPUTS
        assert len(job.inputs.all()) == 2


@pytest.mark.xfail(reason="Still to be addressed for optional inputs pitch")
@pytest.mark.django_db
def test_algorithm_job_post_serializer_create(
    rf, settings, django_capture_on_commit_callbacks
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    # setup
    user = UserFactory()
    upload = RawImageUploadSessionFactory(creator=user)
    image1, image2 = ImageFactory.create_batch(2)
    upload.image_set.set([image1])
    for im in [image1, image2]:
        assign_perm("view_image", user, im)
        assert user.has_perm("view_image", im)

    algorithm_image = AlgorithmImageFactory(
        is_manifest_valid=True, is_in_registry=True, is_desired_version=True
    )
    ci_string = ComponentInterfaceFactory(
        kind=ComponentInterface.Kind.STRING,
        default_value="default",
    )
    ci_img1 = ComponentInterfaceFactory(kind=ComponentInterface.Kind.IMAGE)
    ci_img2 = ComponentInterfaceFactory(kind=ComponentInterface.Kind.IMAGE)

    algorithm_image.algorithm.inputs.set([ci_string, ci_img2, ci_img1])
    algorithm_image.algorithm.add_editor(user)

    job = {
        "algorithm": algorithm_image.algorithm.api_url,
        "inputs": [
            {"interface": ci_img1.slug, "upload_session": upload.api_url},
            {"interface": ci_img2.slug, "image": image2.api_url},
        ],
    }

    # test
    request = rf.get("/foo")
    request.user = user
    serializer = JobPostSerializer(data=job, context={"request": request})

    # verify
    assert serializer.is_valid()
    # fake successful upload
    upload.status = RawImageUploadSession.SUCCESS
    upload.save()

    with django_capture_on_commit_callbacks(execute=True):
        serializer.create(serializer.validated_data)
    assert len(Job.objects.all()) == 1
    job = Job.objects.first()
    assert job.creator == user
    assert len(job.inputs.all()) == 3


@pytest.mark.xfail(reason="Still to be addressed for optional inputs pitch")
@pytest.mark.django_db
class TestJobCreateLimits:
    def test_form_invalid_without_enough_credits(self, rf, settings):
        algorithm_image = AlgorithmImageFactory(
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
            algorithm__minimum_credits_per_job=(
                settings.ALGORITHMS_GENERAL_CREDITS_PER_MONTH_PER_USER + 1
            ),
        )
        algorithm_image.algorithm.inputs.clear()
        user = UserFactory()

        algorithm_image.algorithm.add_user(user=user)

        request = rf.get("/foo")
        request.user = user
        serializer = JobPostSerializer(
            data={
                "algorithm": algorithm_image.algorithm.api_url,
                "inputs": [],
            },
            context={"request": request},
        )

        assert not serializer.is_valid()
        assert serializer.errors == {
            "non_field_errors": [
                ErrorDetail(
                    string="You have run out of algorithm credits",
                    code="invalid",
                )
            ]
        }

    def test_form_valid_for_editor(self, rf, settings):
        algorithm_image = AlgorithmImageFactory(
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
            algorithm__minimum_credits_per_job=(
                settings.ALGORITHMS_GENERAL_CREDITS_PER_MONTH_PER_USER + 1
            ),
        )
        algorithm_image.algorithm.inputs.clear()
        user = UserFactory()

        algorithm_image.algorithm.add_editor(user=user)

        request = rf.get("/foo")
        request.user = user
        serializer = JobPostSerializer(
            data={
                "algorithm": algorithm_image.algorithm.api_url,
                "inputs": [],
            },
            context={"request": request},
        )
        assert serializer.is_valid()
        assert algorithm_image.get_remaining_jobs(user=user) == 5

        AlgorithmJobFactory.create_batch(
            5,
            algorithm_image=algorithm_image,
            creator=user,
            status=Job.SUCCESS,
            time_limit=algorithm_image.algorithm.time_limit,
        )
        serializer = JobPostSerializer(
            data={
                "algorithm": algorithm_image.algorithm.api_url,
                "inputs": [],
            },
            context={"request": request},
        )
        assert not serializer.is_valid()
        assert algorithm_image.get_remaining_jobs(user=user) == 0

    def test_form_valid_with_credits(self, rf):
        algorithm_image = AlgorithmImageFactory(
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
            algorithm__minimum_credits_per_job=1,
        )
        algorithm_image.algorithm.inputs.clear()
        user = UserFactory()

        algorithm_image.algorithm.add_user(user=user)

        request = rf.get("/foo")
        request.user = user
        serializer = JobPostSerializer(
            data={
                "algorithm": algorithm_image.algorithm.api_url,
                "inputs": [],
            },
            context={"request": request},
        )

        assert serializer.is_valid()


@pytest.mark.django_db
def test_reformat_inputs(rf):
    ci_str = ComponentInterfaceFactory(kind=ComponentInterface.Kind.STRING)
    ci_img = ComponentInterfaceFactory(kind=ComponentInterface.Kind.IMAGE)
    ci_img2 = ComponentInterfaceFactory(kind=ComponentInterface.Kind.IMAGE)
    ci_file = ComponentInterfaceFactory(
        kind=ComponentInterface.Kind.ANY, store_in_database=False
    )

    us = RawImageUploadSessionFactory()
    upl = UserUploadFactory()
    im = ImageFactory()

    data = [
        {"interface": ci_str, "value": "foo"},
        {"interface": ci_img, "image": im},
        {"interface": ci_img2, "upload_session": us},
        {"interface": ci_file, "user_upload": upl},
    ]
    request = rf.get("/foo")
    request.user = UserFactory()
    serializer = JobPostSerializer(
        data=AlgorithmJobFactory(time_limit=10), context={"request": request}
    )

    assert serializer.reformat_inputs(serialized_civs=data)[0].value == "foo"
    assert serializer.reformat_inputs(serialized_civs=data)[1].image == im
    assert (
        serializer.reformat_inputs(serialized_civs=data)[2].upload_session
        == us
    )
    assert (
        serializer.reformat_inputs(serialized_civs=data)[3].user_upload == upl
    )


@pytest.mark.xfail(reason="Still to be addressed for optional inputs pitch")
@pytest.mark.django_db
def test_algorithm_post_serializer_image_and_time_limit_fixed(rf):
    request = rf.get("/foo")
    request.user = UserFactory()
    alg = AlgorithmFactory(time_limit=10)
    alg.add_editor(request.user)
    ai = AlgorithmImageFactory(
        algorithm=alg,
        is_desired_version=True,
        is_manifest_valid=True,
        is_in_registry=True,
    )
    different_ai = AlgorithmImageFactory(algorithm=alg)
    ci = ComponentInterfaceFactory(kind=ComponentInterface.Kind.STRING)
    alg.inputs.set([ci])
    serializer = JobPostSerializer(
        data={
            "algorithm": alg.api_url,
            "algorithm_image": different_ai.api_url,
            "algorithm_model": "1234",  # try to provide a pk
            "time_limit": 60,
            "inputs": [{"interface": ci.slug, "value": "bar"}],
        },
        context={"request": request},
    )
    assert serializer.is_valid()
    serializer.create(serializer.validated_data)
    job = Job.objects.get()
    assert job.algorithm_image == ai
    assert job.algorithm_image != different_ai
    assert not job.algorithm_model
    assert job.time_limit == 10
