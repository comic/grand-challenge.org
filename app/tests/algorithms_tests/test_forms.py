import pytest

from grandchallenge.algorithms.models import (
    Algorithm,
    AlgorithmPermissionRequest,
)
from grandchallenge.core.management.commands.init_gc_demo import (
    get_temporary_image,
)
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmPermissionRequestFactory,
)
from tests.algorithms_tests.utils import get_algorithm_creator
from tests.factories import UserFactory, WorkstationFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_editor_update_form(client):
    alg, _ = AlgorithmFactory(), AlgorithmFactory()

    editor = UserFactory()
    alg.editors_group.user_set.add(editor)

    assert alg.editors_group.user_set.count() == 1

    new_editor = UserFactory()
    assert not alg.is_editor(user=new_editor)
    response = get_view_for_user(
        viewname="algorithms:editors-update",
        client=client,
        method=client.post,
        data={"user": new_editor.pk, "action": "ADD"},
        reverse_kwargs={"slug": alg.slug},
        follow=True,
        user=editor,
    )
    assert response.status_code == 200

    alg.refresh_from_db()
    assert alg.editors_group.user_set.count() == 2
    assert alg.is_editor(user=new_editor)

    response = get_view_for_user(
        viewname="algorithms:editors-update",
        client=client,
        method=client.post,
        data={"user": new_editor.pk, "action": "REMOVE"},
        reverse_kwargs={"slug": alg.slug},
        follow=True,
        user=editor,
    )
    assert response.status_code == 200

    alg.refresh_from_db()
    assert alg.editors_group.user_set.count() == 1
    assert not alg.is_editor(user=new_editor)


@pytest.mark.django_db
def test_user_update_form(client):
    alg, _ = AlgorithmFactory(), AlgorithmFactory()

    editor = UserFactory()
    alg.editors_group.user_set.add(editor)

    assert alg.users_group.user_set.count() == 0

    new_user = UserFactory()
    pr = AlgorithmPermissionRequestFactory(user=new_user, algorithm=alg)

    assert not alg.is_user(user=new_user)
    assert pr.status == AlgorithmPermissionRequest.PENDING
    response = get_view_for_user(
        viewname="algorithms:users-update",
        client=client,
        method=client.post,
        data={"user": new_user.pk, "action": "ADD"},
        reverse_kwargs={"slug": alg.slug},
        follow=True,
        user=editor,
    )
    assert response.status_code == 200

    alg.refresh_from_db()
    pr.refresh_from_db()
    assert alg.users_group.user_set.count() == 1
    assert alg.is_user(user=new_user)
    assert pr.status == AlgorithmPermissionRequest.ACCEPTED

    response = get_view_for_user(
        viewname="algorithms:users-update",
        client=client,
        method=client.post,
        data={"user": new_user.pk, "action": "REMOVE"},
        reverse_kwargs={"slug": alg.slug},
        follow=True,
        user=editor,
    )
    assert response.status_code == 200

    alg.refresh_from_db()
    pr.refresh_from_db()
    assert alg.users_group.user_set.count() == 0
    assert not alg.is_user(user=new_user)
    assert pr.status == AlgorithmPermissionRequest.REJECTED


@pytest.mark.django_db
def test_algorithm_create(client):
    # The algorithm creator should automatically get added to the editors group
    creator = get_algorithm_creator()

    ws = WorkstationFactory()

    def try_create_algorithm():
        return get_view_for_user(
            viewname="algorithms:create",
            client=client,
            method=client.post,
            data={
                "title": "foo bar",
                "logo": get_temporary_image(),
                "workstation": ws.pk,
            },
            follow=True,
            user=creator,
        )

    response = try_create_algorithm()
    assert "error_1_id_workstation" in response.rendered_content

    # The editor must have view permissions for the workstation to add it
    ws.add_user(user=creator)

    response = try_create_algorithm()
    assert "error_1_id_workstation" not in response.rendered_content
    assert response.status_code == 200

    alg = Algorithm.objects.get(title="foo bar")

    assert alg.slug == "foo-bar"
    assert alg.is_editor(user=creator)
    assert not alg.is_user(user=creator)
