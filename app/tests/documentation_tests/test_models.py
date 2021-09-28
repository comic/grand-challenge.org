import pytest

from grandchallenge.documentation.models import DocPage
from tests.documentation_tests.factories import DocPageFactory


@pytest.mark.django_db
def test_last_added_page_last_in_order():
    p1 = DocPageFactory()
    p2 = DocPageFactory()

    assert [p1.order, p2.order] == [1, 2]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "move_op,expected",
    [
        (DocPage.UP, [2, 1, 3, 4]),
        (DocPage.DOWN, [1, 3, 2, 4]),
        (DocPage.FIRST, [2, 1, 3, 4]),
        (DocPage.LAST, [1, 4, 2, 3]),
    ],
)
def test_page_move(move_op, expected):
    p1, p2, p3, p4 = (
        DocPageFactory(),
        DocPageFactory(),
        DocPageFactory(),
        DocPageFactory(),
    )

    assert [p1.order, p2.order, p3.order, p4.order] == [1, 2, 3, 4]

    # move second page
    p2.move(move_op)

    for p in [p1, p2, p3, p4]:
        p.refresh_from_db()

    assert [p.order for p in [p1, p2, p3, p4]] == expected


@pytest.mark.django_db
def test_next():
    p1 = DocPageFactory()
    p2 = DocPageFactory()

    assert [p1.order, p2.order] == [1, 2]
    assert p1.next == p2
