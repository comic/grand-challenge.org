import pytest

from tests.blogs_tests.factory import PostFactory


@pytest.mark.django_db
def test_created_updated_when_published():
    p = PostFactory()
    assert p.published is False

    created = p.created

    p.published = True
    p.save()

    p.refresh_from_db()

    assert p.created > created
