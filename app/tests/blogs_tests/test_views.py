import pytest
from guardian.shortcuts import assign_perm

from tests.blogs_tests.factory import PostFactory
from tests.factories import UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_author_add_button_visibility(client):
    p = PostFactory()
    u = UserFactory()

    response = get_view_for_user(
        client=client,
        viewname="blogs:detail",
        reverse_kwargs={"slug": p.slug},
        user=u,
    )

    assert "Add Author" not in response.rendered_content

    # give user permission to edit the blog post
    assign_perm("blogs.change_post", u, p)

    response = get_view_for_user(
        client=client,
        viewname="blogs:detail",
        reverse_kwargs={"slug": p.slug},
        user=u,
    )

    assert "Add Author" in response.rendered_content
