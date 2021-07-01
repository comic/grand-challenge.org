import pytest
from guardian.shortcuts import assign_perm, remove_perm

from tests.evaluation_tests.factories import PhaseFactory
from tests.factories import UserFactory
from tests.utils import get_view_for_user
from tests.workspaces_tests.factories import WorkspaceFactory


@pytest.mark.django_db
class TestObjectPermissionRequiredViews:
    def test_permission_required_views(self, client):
        p = PhaseFactory()
        w = WorkspaceFactory(phase=p)
        u = UserFactory()

        for view_name, kwargs, permission, obj, redirect in [
            (
                "create",
                {
                    "challenge_short_name": p.challenge.short_name,
                    "slug": p.slug,
                },
                "create_phase_workspace",
                p,
                None,
            ),
            (
                "detail",
                {
                    "challenge_short_name": w.phase.challenge.short_name,
                    "pk": w.pk,
                },
                "view_workspace",
                w,
                None,
            ),
        ]:

            def _get_view():
                return get_view_for_user(
                    client=client,
                    viewname=f"workspaces:{view_name}",
                    reverse_kwargs=kwargs,
                    user=u,
                )

            response = _get_view()
            if redirect is not None:
                assert response.status_code == 302
                assert response.url == redirect
            else:
                assert response.status_code == 403

            assign_perm(permission, u, obj)

            response = _get_view()
            assert response.status_code == 200

            remove_perm(permission, u, obj)

    def test_permission_required_list_views(self, client):
        w = WorkspaceFactory()
        u = UserFactory()

        for view_name, kwargs, permission, objs in [
            (
                "list",
                {"challenge_short_name": w.phase.challenge.short_name},
                "view_workspace",
                {w},
            ),
        ]:

            def _get_view():
                return get_view_for_user(
                    client=client,
                    viewname=f"workspaces:{view_name}",
                    reverse_kwargs=kwargs,
                    user=u,
                )

            response = _get_view()
            assert response.status_code == 200
            assert set() == {*response.context[-1]["object_list"]}

            assign_perm(permission, u, list(objs))

            response = _get_view()
            assert response.status_code == 200
            assert objs == {*response.context[-1]["object_list"]}

            for obj in objs:
                remove_perm(permission, u, obj)
