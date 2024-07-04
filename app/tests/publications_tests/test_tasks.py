import pytest

from grandchallenge.publications.models import Publication
from grandchallenge.publications.tasks import update_publication_metadata
from tests.algorithms_tests.factories import AlgorithmFactory
from tests.archives_tests.factories import ArchiveFactory
from tests.factories import ChallengeFactory
from tests.reader_studies_tests.factories import ReaderStudyFactory

ARXIV_IDENTIFIER = "1234.56789"
ARXIV_CSL = {
    "type": "manuscript",
    "title": "arXiv title",
    "DOI": "10.1234/s123new.doi",
}
DOI_CSL = {
    "type": "journal-article",
    "title": "doi title",
}


@pytest.mark.django_db
def test_update_publication_metadata(mocker):
    mocker.patch(
        "grandchallenge.publications.fields.get_arxiv_csl",
        return_value=ARXIV_CSL,
    )
    mocker.patch(
        "grandchallenge.publications.fields.get_doi_csl",
        return_value=DOI_CSL,
    )

    publication = Publication.objects.create(
        identifier=ARXIV_IDENTIFIER, csl=ARXIV_CSL
    )

    assert publication.csl["title"] == "arXiv title"
    assert str(publication.identifier) == ARXIV_IDENTIFIER

    update_publication_metadata()

    publication.refresh_from_db()

    assert publication.csl["title"] == "doi title"
    assert str(publication.identifier) == ARXIV_CSL["DOI"]


@pytest.mark.django_db
def test_duplicate_publication_merging(mocker):
    mocker.patch(
        "grandchallenge.publications.fields.get_arxiv_csl",
        return_value=ARXIV_CSL,
    )
    mocker.patch(
        "grandchallenge.publications.fields.get_doi_csl",
        return_value=DOI_CSL,
    )

    new_publication = Publication.objects.create(
        identifier=ARXIV_CSL["DOI"], csl=DOI_CSL
    )
    old_publication = Publication.objects.create(
        identifier=ARXIV_IDENTIFIER, csl=ARXIV_CSL
    )

    c1, c2, c3 = ChallengeFactory.create_batch(3)
    a1, a2 = AlgorithmFactory.create_batch(2)
    ar1, ar2 = ArchiveFactory.create_batch(2)
    rs1 = ReaderStudyFactory()

    new_publication.challenge_set.add(c1)
    new_publication.algorithm_set.add(a1)
    new_publication.archive_set.add(ar1)
    new_publication.readerstudy_set.add(rs1)

    old_publication.challenge_set.add(c2, c3)
    old_publication.algorithm_set.add(a1, a2)
    old_publication.archive_set.add(ar2)

    assert Publication.objects.count() == 2
    assert new_publication.challenge_set.count() == 1
    assert new_publication.algorithm_set.count() == 1
    assert new_publication.archive_set.count() == 1
    assert new_publication.readerstudy_set.count() == 1

    # Only these fields should be copied over
    assert Publication.get_reverse_many_to_many_fields() == [
        "challenge_set",
        "algorithm_set",
        "archive_set",
        "readerstudy_set",
    ]

    update_publication_metadata()

    new_publication.refresh_from_db()
    with pytest.raises(Publication.DoesNotExist):
        old_publication.refresh_from_db()

    assert Publication.objects.count() == 1
    assert new_publication.title == "doi title"
    assert str(new_publication.identifier) == ARXIV_CSL["DOI"]
    assert new_publication.challenge_set.count() == 3
    assert new_publication.algorithm_set.count() == 2
    assert new_publication.archive_set.count() == 2
    assert new_publication.readerstudy_set.count() == 1
