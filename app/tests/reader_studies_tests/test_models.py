import pytest
from django.core.exceptions import ObjectDoesNotExist

from grandchallenge.reader_studies.models import ReaderStudy
from tests.reader_studies_tests.factories import ReaderStudyFactory


@pytest.mark.django_db
def test_group_deletion():
    rs = ReaderStudyFactory()
    readers_group = rs.readers_group
    editors_group = rs.editors_group

    assert readers_group
    assert editors_group

    ReaderStudy.objects.filter(pk__in=[rs.pk]).delete()

    with pytest.raises(ObjectDoesNotExist):
        readers_group.refresh_from_db()

    with pytest.raises(ObjectDoesNotExist):
        editors_group.refresh_from_db()


@pytest.mark.django_db
@pytest.mark.parametrize("group", ["readers_group", "editors_group"])
def test_group_deletion_reverse(group):
    rs = ReaderStudyFactory()
    readers_group = rs.readers_group
    editors_group = rs.editors_group

    assert readers_group
    assert editors_group

    getattr(rs, group).delete()

    with pytest.raises(ObjectDoesNotExist):
        readers_group.refresh_from_db()

    with pytest.raises(ObjectDoesNotExist):
        editors_group.refresh_from_db()

    with pytest.raises(ObjectDoesNotExist):
        rs.refresh_from_db()
