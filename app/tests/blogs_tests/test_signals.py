import pytest

from tests.blogs_tests.factory import PostFactory
from tests.evaluation_tests.test_permissions import get_users_with_set_perms
from tests.factories import UserFactory


@pytest.mark.django_db
@pytest.mark.parametrize("reverse", [True, False])
def test_post_authors_permissions_signal(client, reverse):
    p1, p2 = PostFactory.create_batch(2)
    u1, u2, u3, u4 = UserFactory.create_batch(4)

    # Remove permissions from the default created user
    p1.authors.clear()
    p2.authors.clear()

    if reverse:
        for user in [u1, u2, u3, u4]:
            user.blog_authors.add(p1, p2)
        for user in [u3, u4]:
            user.blog_authors.remove(p1, p2)
        for user in [u1, u2]:
            user.blog_authors.remove(p2)
    else:
        # Test that adding authors works
        p1.authors.add(u1, u2, u3, u4)
        # Test that removing authors works
        p1.authors.remove(u3, u4)

    assert get_users_with_set_perms(p1) == {
        u1: {"change_post"},
        u2: {"change_post"},
    }
    assert get_users_with_set_perms(p2) == {}

    # Test clearing
    if reverse:
        u1.blog_authors.clear()
        u2.blog_authors.clear()
    else:
        p1.authors.clear()

    assert get_users_with_set_perms(p1) == {}
    assert get_users_with_set_perms(p2) == {}
