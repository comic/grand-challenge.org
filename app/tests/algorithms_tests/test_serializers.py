import pytest

from grandchallenge.algorithms.serializers import (
    AlgorithmImageSerializer,
    AlgorithmSerializer,
    HyperlinkedJobSerializer,
    JobPostSerializer,
)
from grandchallenge.components.models import ComponentInterface
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
    AlgorithmJobFactory,
)
from tests.components_tests.factories import ComponentInterfaceFactory
from tests.factories import UserFactory
from tests.serializer_helpers import (
    do_test_serializer_fields,
    do_test_serializer_valid,
)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "serializer_data",
    (
        (
            {
                "unique": True,
                "factory": AlgorithmFactory,
                "serializer": AlgorithmSerializer,
                "fields": (
                    "api_url",
                    "url",
                    "description",
                    "pk",
                    "title",
                    "logo",
                    "slug",
                    "average_duration",
                    "inputs",
                    "outputs",
                ),
            },
            {
                "unique": True,
                "factory": AlgorithmImageFactory,
                "serializer": AlgorithmImageSerializer,
                "fields": ["pk", "api_url", "algorithm"],
            },
        )
    ),
)
class TestSerializers:
    def test_serializer_valid(self, serializer_data, rf):
        do_test_serializer_valid(serializer_data, request=rf.get("/foo"))

    def test_serializer_fields(self, serializer_data, rf):
        do_test_serializer_fields(serializer_data, request=rf.get("/foo"))


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
            "Component interface testinterface-3 does not exist.",
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
        "algorithm_slug": algorithm_image.algorithm.slug,
        "inputs": [
            {"interface_slug": interface, "value": "dummy"}
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
