import pytest

from grandchallenge.algorithms.serializers import JobSerializer
from grandchallenge.archives.serializers import ArchiveItemSerializer
from grandchallenge.reader_studies.serializers import DisplaySetSerializer
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmJobFactory,
)
from tests.archives_tests.factories import ArchiveFactory, ArchiveItemFactory
from tests.factories import UserFactory
from tests.hanging_protocols_tests.factories import HangingProtocolFactory
from tests.reader_studies_tests.factories import (
    DisplaySetFactory,
    ReaderStudyFactory,
)


@pytest.mark.parametrize(
    "factory,item_factory,relation,serializer",
    (
        (
            AlgorithmFactory,
            AlgorithmJobFactory,
            "algorithm_image__algorithm",
            JobSerializer,
        ),
        (ArchiveFactory, ArchiveItemFactory, "archive", ArchiveItemSerializer),
        (
            ReaderStudyFactory,
            DisplaySetFactory,
            "reader_study",
            DisplaySetSerializer,
        ),
    ),
)
@pytest.mark.django_db
def test_hanging_protocol_serializer_field(
    rf, factory, item_factory, relation, serializer
):
    """Each item should get the hanging protocol and content from the parent"""
    hp = HangingProtocolFactory()
    object = factory(hanging_protocol=hp, view_content={"main": "test"})

    item = item_factory(**{relation: object})

    request = rf.get("/foo")
    request.user = UserFactory()

    serializer = serializer(item, context={"request": request})

    assert serializer.data["hanging_protocol"]["json"] == hp.json
    assert serializer.data["view_content"] == {"main": "test"}


# def test_optional_hanging_protocol_serializer_field(

# )
