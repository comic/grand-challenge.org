import pytest
from guardian.shortcuts import assign_perm, remove_perm

from tests.blogs_tests.factory import PostFactory
from tests.factories import UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
class TestObjectPermissionRequiredViews:
    def test_permission_required_views(self, client):
        p = PostFactory()
        u = UserFactory()

        for view_name, kwargs, permission, obj in [
            ("create", {}, "blogs.add_post", None),
            ("update", {"slug": p.slug}, "blogs.change_post", p,),
            ("authors-update", {"slug": p.slug}, "blogs.change_post", p,),
        ]:

            def _get_view():
                return get_view_for_user(
                    client=client,
                    viewname=f"blogs:{view_name}",
                    reverse_kwargs=kwargs,
                    user=u,
                )

            response = _get_view()
            assert response.status_code == 403

            assign_perm(permission, u, obj)

            response = _get_view()
            assert response.status_code == 200

            remove_perm(permission, u, obj)
