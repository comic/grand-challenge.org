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
    "factory,item_factory,item_factory_kwargs,relation,serializer",
    (
        (
            AlgorithmFactory,
            AlgorithmJobFactory,
            {"time_limit": 60},
            "algorithm_image__algorithm",
            JobSerializer,
        ),
        (
            ArchiveFactory,
            ArchiveItemFactory,
            {},
            "archive",
            ArchiveItemSerializer,
        ),
        (
            ReaderStudyFactory,
            DisplaySetFactory,
            {},
            "reader_study",
            DisplaySetSerializer,
        ),
    ),
)
@pytest.mark.django_db
class TestHangingProtocolSerializer:
    def test_hanging_protocol_serializer_field(
        self,
        rf,
        factory,
        item_factory,
        item_factory_kwargs,
        relation,
        serializer,
    ):
        """Each item should get the hanging protocol and content from the parent"""
        hp = HangingProtocolFactory(json=[{"viewport_name": "main"}])
        instance = factory(hanging_protocol=hp, view_content={"main": "test"})

        item_factory_kwargs.update({relation: instance})

        item = item_factory(**item_factory_kwargs)

        request = rf.get("/foo")
        request.user = UserFactory()

        serializer = serializer(item, context={"request": request})

        assert serializer.data["hanging_protocol"]["json"] == hp.json
        assert serializer.data["hanging_protocol"]["title"] == hp.title
        assert serializer.data["hanging_protocol"]["pk"] == str(hp.pk)
        assert serializer.data["view_content"] == {"main": "test"}
        assert (
            serializer.data["hanging_protocol"]["svg_icon"]
            == """<svg width="32" height="18" fill-opacity="0"><rect x="0.8" y="0.8" width="30.4" height="16.4" stroke-width="1.6" /></svg>"""
        )

    def test_optional_hanging_protocol_serializer_field(
        self,
        rf,
        factory,
        item_factory,
        item_factory_kwargs,
        relation,
        serializer,
    ):
        """Each item should get the optional hanging protocol from the parent"""
        hps = HangingProtocolFactory.create_batch(3)
        instance = factory()
        instance.optional_hanging_protocols.set(hps)

        item_factory_kwargs.update({relation: instance})

        item = item_factory(**item_factory_kwargs)

        request = rf.get("/foo")
        request.user = UserFactory()

        serializer = serializer(item, context={"request": request})
        assert len(serializer.data["optional_hanging_protocols"]) == 3
        for protocol in serializer.data["optional_hanging_protocols"]:
            hp = next(x for x in hps if protocol["pk"] == str(x.pk))
            assert protocol["json"] == hp.json
            assert protocol["title"] == hp.title
            assert protocol["svg_icon"] == hp.svg_icon

    def test_no_optional_hanging_protocol_serializer_field(
        self,
        rf,
        factory,
        item_factory,
        item_factory_kwargs,
        relation,
        serializer,
    ):
        """If no optional hanging protocols are present, none should be serialized"""
        instance = factory()

        item_factory_kwargs.update({relation: instance})

        item = item_factory(**item_factory_kwargs)

        request = rf.get("/foo")
        request.user = UserFactory()

        serializer = serializer(item, context={"request": request})

        assert serializer.data["optional_hanging_protocols"] == []
