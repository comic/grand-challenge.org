import pytest

from grandchallenge.profiles.templatetags.profiles import (
    user_profile_links_from_usernames,
)
from tests.factories import UserFactory


@pytest.mark.django_db
def test_user_profile_links_from_usernames(django_assert_max_num_queries):
    users = UserFactory.create_batch(4)
    with django_assert_max_num_queries(
        2,  # User model getter requires a single query + actual queryset
    ):
        user_profile_links = user_profile_links_from_usernames(
            [user.username for user in users]
        )
    assert len(user_profile_links.keys()) == len(users)
