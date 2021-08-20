import pytest
from guardian.shortcuts import assign_perm

from grandchallenge.algorithms.models import Job
from grandchallenge.algorithms.serializers import (
    HyperlinkedJobSerializer,
    JobPostSerializer,
)
from grandchallenge.components.models import ComponentInterface
from tests.algorithms_tests.factories import (
    AlgorithmImageFactory,
    AlgorithmJobFactory,
)
from tests.cases_tests.factories import RawImageUploadSessionFactory
from tests.components_tests.factories import ComponentInterfaceFactory
from tests.factories import ImageFactory, UserFactory


@pytest.mark.django_db
def test_algorithm_title_on_job_serializer(rf):
    job = AlgorithmJobFactory()
    serializer = HyperlinkedJobSerializer(
        job, context={"request": rf.get("/foo")}
    )
    assert (
        serializer.data["algorithm_title"]
        == job.algorithm_image.algorithm.title
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "title, "
    "add_user, "
    "image_ready, "
    "algorithm_interface_titles, "
    "job_interface_slugs, "
    "error_message",
    (
        (
            "algorithm1",
            False,
            False,
            ("TestInterface 1",),
            ("testinterface-1",),
            "User does not have permission to use algorithm algorithm1",
        ),
        (
            "algorithm1",
            True,
            False,
            ("TestInterface 1",),
            ("testinterface-1",),
            "Algorithm image is not ready to be used",
        ),
        (
            "algorithm1",
            True,
            True,
            ("TestInterface 1",),
            ("testinterface-3",),
            "Object with slug=testinterface-3 does not exist.",
        ),
        (
            "algorithm1",
            True,
            True,
            ("TestInterface 1", "TestInterface 2"),
            ("testinterface-1",),
            "Interface(s) TestInterface 2 do not have a default value and should be provided.",
        ),
        (
            "algorithm1",
            True,
            True,
            ("TestInterface 1",),
            ("testinterface-1", "testinterface-2"),
            "Provided inputs(s) TestInterface 2 are not defined for this algorithm",
        ),
        (
            "algorithm1",
            True,
            True,
            ("TestInterface 1", "TestInterface 2"),
            ("testinterface-1", "testinterface-2"),
            None,
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
    algorithm_image = AlgorithmImageFactory(ready=image_ready)
    algorithm_image.algorithm.title = title
    algorithm_image.algorithm.inputs.set(
        [interfaces[title] for title in algorithm_interface_titles]
    )
    if add_user:
        algorithm_image.algorithm.add_editor(user)

    algorithm_image.algorithm.save()

    job = {
        "algorithm": algorithm_image.algorithm.api_url,
        "inputs": [
            {"interface": interface, "value": "dummy"}
            for interface in job_interface_slugs
        ],
    }

    # test
    serializer = JobPostSerializer(
        data=job, context={"request": rf.get("/foo"), "user": user}
    )

    # verify
    assert serializer.is_valid() == (error_message is None)
    if error_message:
        assert error_message in str(serializer.errors)
    else:
        assert len(Job.objects.all()) == 0
        serializer.create(serializer.validated_data)
        assert len(Job.objects.all()) == 1
        job = Job.objects.first()
        assert job.status == job.PENDING
        assert len(job.inputs.all()) == 2


@pytest.mark.django_db
def test_algorithm_job_post_serializer_create(rf):
    # setup
    user = UserFactory()
    upload, upload_2 = (
        RawImageUploadSessionFactory(creator=user),
        RawImageUploadSessionFactory(creator=user),
    )
    image = ImageFactory()
    upload_2.image_set.set([image])
    assign_perm("view_image", user, image)
    assert user.has_perm("view_image", image)
    algorithm_image = AlgorithmImageFactory(ready=True)
    interfaces = {
        ComponentInterfaceFactory(
            kind=ComponentInterface.Kind.STRING,
            title="TestInterface 1",
            default_value="default",
        ),
        ComponentInterfaceFactory(
            kind=ComponentInterface.Kind.IMAGE, title="TestInterface 2"
        ),
        ComponentInterfaceFactory(
            kind=ComponentInterface.Kind.IMAGE, title="TestInterface 3"
        ),
    }
    algorithm_image.algorithm.inputs.set(interfaces)
    algorithm_image.algorithm.add_editor(user)

    algorithm_image.algorithm.save()

    job = {"algorithm": algorithm_image.algorithm.api_url, "inputs": []}
    job["inputs"].append(
        {"interface": "testinterface-2", "upload_session": upload.api_url}
    )
    job["inputs"].append(
        {"interface": "testinterface-3", "image": image.api_url}
    )

    # test
    serializer = JobPostSerializer(
        data=job, context={"request": rf.get("/foo"), "user": user}
    )

    # verify
    assert serializer.is_valid()
    serializer.create(serializer.validated_data)
    assert len(Job.objects.all()) == 1
    job = Job.objects.first()
    assert job.creator == user
    assert len(job.inputs.all()) == 3
