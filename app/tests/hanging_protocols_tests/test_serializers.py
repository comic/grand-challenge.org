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
class TestHangingProtocolSerializer:
    def test_hanging_protocol_serializer_field(
        self, rf, factory, item_factory, relation, serializer
    ):
        """Each item should get the hanging protocol and content from the parent"""
        hp = HangingProtocolFactory()
        object = factory(hanging_protocol=hp, view_content={"main": "test"})

        item = item_factory(**{relation: object})

        request = rf.get("/foo")
        request.user = UserFactory()

        serializer = serializer(item, context={"request": request})
        assert serializer.data["hanging_protocol"]["json"] == hp.json
        assert serializer.data["hanging_protocol"]["title"] == hp.title
        assert serializer.data["hanging_protocol"]["id"] == str(hp.id)
        assert serializer.data["view_content"] == {"main": "test"}

    def test_optional_hanging_protocol_serializer_field(
        self, rf, factory, item_factory, relation, serializer
    ):
        """Each item should get the optional hanging protocol from the parent"""
        hps = HangingProtocolFactory.create_batch(3)
        object = factory()
        object.optional_hanging_protocols.set(hps)
        item = item_factory(**{relation: object})

        request = rf.get("/foo")
        request.user = UserFactory()
        serializer = serializer(item, context={"request": request})
        assert len(serializer.data["optional_hanging_protocols"]) == 3
        for protocol in serializer.data["optional_hanging_protocols"]:
            assert protocol["id"]

            """get an element by id from the hanging protocol list"""
            hp = next(x for x in hps if protocol["id"] == str(x.id))

            """check that the element with matching id has matching title and json"""
            assert protocol["json"] == hp.json
            assert protocol["title"] == hp.title

    def test_no_optional_hanging_protocol_serializer_field(
        self, rf, factory, item_factory, relation, serializer
    ):
        """If no optional hanging protocols are present, none should be serialized"""
        object = factory()

        item = item_factory(**{relation: object})

        request = rf.get("/foo")
        request.user = UserFactory()

        serializer = serializer(item, context={"request": request})

        assert serializer.data["optional_hanging_protocols"] == []
