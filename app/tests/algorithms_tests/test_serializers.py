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
    AlgorithmInterfaceFactory,
    AlgorithmJobFactory,
)
from tests.cases_tests.factories import RawImageUploadSessionFactory
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.factories import ImageFactory, UserFactory


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
            "The set of inputs provided does not match any of the algorithm's interfaces.",
            False,
        ),
        (
            "algorithm1",
            True,
            True,
            ("TestInterface 1",),
            ("testinterface-1", "testinterface-2"),
            "The set of inputs provided does not match any of the algorithm's interfaces.",
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
    interface = AlgorithmInterfaceFactory(
        inputs=[interfaces[title] for title in algorithm_interface_titles]
    )
    algorithm_image.algorithm.interfaces.add(interface)

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
            {"interface": int, "value": "dummy"} for int in job_interface_slugs
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
    ci_img1 = ComponentInterfaceFactory(
        kind=ComponentInterface.Kind.PANIMG_IMAGE
    )
    ci_img2 = ComponentInterfaceFactory(
        kind=ComponentInterface.Kind.PANIMG_IMAGE
    )

    interface = AlgorithmInterfaceFactory(inputs=[ci_string, ci_img2, ci_img1])
    algorithm_image.algorithm.interfaces.add(interface)
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

    # all inputs need to be provided, also those with default value
    assert not serializer.is_valid()

    # add missing input
    job = {
        "algorithm": algorithm_image.algorithm.api_url,
        "inputs": [
            {
                "interface": ci_img1.slug,
                "upload_session": upload.api_url,
                # Other attributes are optionally None
                "user_upload": None,
                "image": None,
                "value": None,
                "file": None,
            },
            {"interface": ci_img2.slug, "image": image2.api_url},
            {"interface": ci_string.slug, "value": "foo"},
        ],
    }
    serializer = JobPostSerializer(data=job, context={"request": request})

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
    assert job.algorithm_interface == interface


@pytest.mark.django_db
class TestJobCreateLimits:
    def test_form_invalid_with_too_many_jobs(self, rf, settings):
        algorithm_image = AlgorithmImageFactory(
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
            algorithm__minimum_credits_per_job=0,
        )
        user = UserFactory()

        settings.ALGORITHMS_MAX_ACTIVE_JOBS_PER_USER = 1

        algorithm_image.algorithm.add_user(user=user)

        AlgorithmJobFactory(creator=user, time_limit=100)

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
                    string="You have too many active jobs, please try again after they have completed",
                    code="invalid",
                )
            ]
        }

    def test_form_invalid_without_enough_credits(self, rf, settings):
        algorithm_image = AlgorithmImageFactory(
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
            algorithm__minimum_credits_per_job=(
                settings.ALGORITHMS_GENERAL_CREDITS_PER_MONTH_PER_USER + 1
            ),
        )
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
        user = UserFactory()

        algorithm_image.algorithm.add_editor(user=user)
        ci = ComponentInterfaceFactory(kind=ComponentInterface.Kind.STRING)
        interface = AlgorithmInterfaceFactory(inputs=[ci])
        algorithm_image.algorithm.interfaces.add(interface)

        request = rf.get("/foo")
        request.user = user
        serializer = JobPostSerializer(
            data={
                "algorithm": algorithm_image.algorithm.api_url,
                "inputs": [
                    {"interface": ci.slug, "value": "foo"},
                ],
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
                "inputs": [
                    {"interface": ci.slug, "value": "foo"},
                ],
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
        user = UserFactory()

        algorithm_image.algorithm.add_user(user=user)
        ci = ComponentInterfaceFactory(kind=ComponentInterface.Kind.STRING)
        interface = AlgorithmInterfaceFactory(inputs=[ci])
        algorithm_image.algorithm.interfaces.add(interface)

        request = rf.get("/foo")
        request.user = user
        serializer = JobPostSerializer(
            data={
                "algorithm": algorithm_image.algorithm.api_url,
                "inputs": [
                    {"interface": ci.slug, "value": "foo"},
                ],
            },
            context={"request": request},
        )

        assert serializer.is_valid()


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
    interface = AlgorithmInterfaceFactory(inputs=[ci])
    alg.interfaces.add(interface)

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


@pytest.mark.parametrize(
    "inputs, interface",
    (
        ([1], 1),  # matches interface 1 of algorithm
        ([1, 2], 2),  # matches interface 2 of algorithm
        ([3, 4, 5], 3),  # matches interface 3 of algorithm
        ([4], None),  # matches interface 4, but not configured for algorithm
        (
            [1, 2, 3],
            None,
        ),  # matches interface 5, but not configured for algorithm
        ([2], None),  # matches no interface (implements part of interface 2)
        (
            [1, 3, 4],
            None,
        ),  # matches no interface (implements interface 3 and an additional input)
    ),
)
@pytest.mark.django_db
def test_validate_inputs_on_job_serializer(inputs, interface, rf):
    user = UserFactory()
    algorithm = AlgorithmFactory()
    algorithm.add_editor(user)
    AlgorithmImageFactory(
        algorithm=algorithm,
        is_desired_version=True,
        is_manifest_valid=True,
        is_in_registry=True,
    )

    io1, io2, io3, io4, io5 = AlgorithmInterfaceFactory.create_batch(5)
    ci1, ci2, ci3, ci4, ci5, ci6 = ComponentInterfaceFactory.create_batch(
        6, kind=ComponentInterface.Kind.STRING
    )

    interfaces = [io1, io2, io3]
    cis = [ci1, ci2, ci3, ci4, ci5, ci6]

    io1.inputs.set([ci1])
    io2.inputs.set([ci1, ci2])
    io3.inputs.set([ci3, ci4, ci5])
    io4.inputs.set([ci1, ci2, ci3])
    io5.inputs.set([ci4])
    io1.outputs.set([ci6])
    io2.outputs.set([ci3])
    io3.outputs.set([ci1])
    io4.outputs.set([ci1])
    io5.outputs.set([ci1])

    algorithm.interfaces.add(io1)
    algorithm.interfaces.add(io2)
    algorithm.interfaces.add(io3)

    algorithm_interface = interfaces[interface - 1] if interface else None
    inputs = [cis[i - 1] for i in inputs]

    job = {
        "algorithm": algorithm.api_url,
        "inputs": [
            {"interface": int.slug, "value": "dummy"} for int in inputs
        ],
    }

    request = rf.get("/foo")
    request.user = user
    serializer = JobPostSerializer(data=job, context={"request": request})

    if interface:
        assert serializer.is_valid()
        assert (
            serializer.validated_data["algorithm_interface"]
            == algorithm_interface
        )
    else:
        assert not serializer.is_valid()
        assert (
            "The set of inputs provided does not match any of the algorithm's interfaces."
            in str(serializer.errors)
        )
        assert "algorithm_interface" not in serializer.validated_data
