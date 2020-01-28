import pytest

from tests.factories import ImageFactory, UserFactory
from tests.reader_studies_tests.factories import (
    AnswerFactory,
    QuestionFactory,
    ReaderStudyFactory,
)
from tests.reader_studies_tests.utils import TwoReaderStudies
from tests.utils import get_view_for_user


@pytest.mark.django_db
@pytest.mark.parametrize("reverse", [True, False])
def test_reader_can_download_images(client, reverse):
    rs_set = TwoReaderStudies()

    im1, im2, im3, im4 = (
        ImageFactory(),
        ImageFactory(),
        ImageFactory(),
        ImageFactory(),
    )

    if reverse:
        for im in [im1, im2, im3, im4]:
            im.readerstudies.add(rs_set.rs1, rs_set.rs2)
        for im in [im3, im4]:
            im.readerstudies.remove(rs_set.rs1, rs_set.rs2)
        for im in [im1, im2]:
            im.readerstudies.remove(rs_set.rs2)
    else:
        # Test that adding images works
        rs_set.rs1.images.add(im1, im2, im3, im4)
        # Test that removing images works
        rs_set.rs1.images.remove(im3, im4)

    tests = (
        (None, 401, []),
        (rs_set.creator, 200, []),
        (rs_set.editor1, 200, []),
        (rs_set.reader1, 200, [im1.pk, im2.pk]),
        (rs_set.editor2, 200, []),
        (rs_set.reader2, 200, []),
        (rs_set.u, 200, []),
    )

    for test in tests:
        response = get_view_for_user(
            viewname="api:image-list",
            client=client,
            user=test[0],
            content_type="application/json",
        )
        assert response.status_code == test[1]

        if test[1] != 401:
            # We provided auth details and get a response
            assert response.json()["count"] == len(test[2])

            pks = [obj["pk"] for obj in response.json()["results"]]

            for pk in test[2]:
                assert str(pk) in pks

    # Test clearing
    if reverse:
        im1.readerstudies.clear()
        im2.readerstudies.clear()
    else:
        rs_set.rs1.images.clear()

    response = get_view_for_user(
        viewname="api:image-list",
        client=client,
        user=rs_set.reader1,
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["count"] == 0


@pytest.mark.django_db
def test_assign_score(settings):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    rs = ReaderStudyFactory()
    im = ImageFactory()
    q = QuestionFactory(reader_study=rs)
    e, r1, r2 = UserFactory(), UserFactory(), UserFactory()

    rs.images.add(im)
    rs.add_editor(e)
    rs.add_reader(r1)
    rs.add_reader(r2)

    a1 = AnswerFactory(question=q, creator=r1, answer="foo")
    a1.images.add(im)
    assert a1.score is None

    gt = AnswerFactory(
        question=q, creator=e, answer="foo", is_ground_truth=True
    )
    gt.images.add(im)
    a1.refresh_from_db()
    assert a1.score == 1.0

    a2 = AnswerFactory(question=q, creator=r2, answer="foo")
    a2.images.add(im)
    a2.refresh_from_db()
    assert a2.score == 1.0
