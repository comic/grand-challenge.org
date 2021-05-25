import pytest

from grandchallenge.algorithms.serializers import (
    AlgorithmImageSerializer,
    AlgorithmSerializer,
    HyperlinkedJobSerializer,
)
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
    AlgorithmJobFactory,
)
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
