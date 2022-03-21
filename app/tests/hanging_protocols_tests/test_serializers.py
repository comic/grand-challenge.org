import pytest

from grandchallenge.algorithms.serializers import AlgorithmSerializer
from grandchallenge.archives.serializers import ArchiveSerializer
from grandchallenge.reader_studies.serializers import ReaderStudySerializer
from tests.algorithms_tests.factories import AlgorithmFactory
from tests.archives_tests.factories import ArchiveFactory
from tests.factories import UserFactory
from tests.hanging_protocols_tests.factories import HangingProtocolFactory
from tests.reader_studies_tests.factories import ReaderStudyFactory


@pytest.mark.parametrize(
    "factory,serializer",
    (
        (AlgorithmFactory, AlgorithmSerializer),
        (ArchiveFactory, ArchiveSerializer),
        (ReaderStudyFactory, ReaderStudySerializer),
    ),
)
@pytest.mark.django_db
def test_hanging_protocol_serializer_field(rf, factory, serializer):
    hp = HangingProtocolFactory()
    object = factory(hanging_protocol=hp)
    request = rf.get("/foo")
    request.user = UserFactory()
    serializer = serializer(object, context={"request": request})
    assert serializer.data["hanging_protocol"]["json"] == hp.json
