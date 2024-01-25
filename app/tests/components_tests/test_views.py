import json

import pytest
from django.conf import settings

from grandchallenge.archives.models import ArchiveItem
from grandchallenge.reader_studies.models import DisplaySet, ReaderStudy
from tests.archives_tests.factories import ArchiveFactory, ArchiveItemFactory
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.factories import UserFactory
from tests.reader_studies_tests.factories import (
    DisplaySetFactory,
    ReaderStudyFactory,
)
from tests.utils import get_view_for_user


@pytest.mark.django_db
class TestComponentInterfaceListView:
    def test_login_required(self, client):
        def _get_view(user, context):
            return get_view_for_user(
                client=client,
                viewname=f"components:component-interface-list-{context}",
                user=user,
            )

        for context in (
            "algorithms",
            "archives",
            "reader-studies",
            "input",
            "output",
        ):
            response = _get_view(user=None, context=context)
            assert response.status_code == 302
            assert settings.LOGIN_URL in response.url

            response = _get_view(user=UserFactory(), context=context)
            assert response.status_code == 200


@pytest.mark.django_db
def test_component_interface_autocomplete(client):
    ci_json = ComponentInterfaceFactory(title="test-json", kind="JSON")
    ci_img = ComponentInterfaceFactory(title="test-img", kind="IMG")
    ci_img_2 = ComponentInterfaceFactory(title="foo-img", kind="IMG")
    user = UserFactory()

    response = get_view_for_user(
        client=client,
        viewname="components:component-interface-autocomplete",
        user=user,
    )
    assert response.status_code == 200
    ids = [x["id"] for x in response.json()["results"]]
    assert str(ci_img.id) in ids
    assert str(ci_img_2.id) in ids
    assert str(ci_json.id) not in ids

    response = get_view_for_user(
        client=client,
        viewname="components:component-interface-autocomplete",
        user=user,
        data={"q": "test"},
    )
    assert response.status_code == 200
    ids = [x["id"] for x in response.json()["results"]]
    assert str(ci_img.id) in ids
    assert str(ci_img_2.id) not in ids
    assert str(ci_json.id) not in ids

    response = get_view_for_user(
        client=client,
        viewname="components:component-interface-autocomplete",
        user=user,
        data={"q": "foo"},
    )
    assert response.status_code == 200
    ids = [x["id"] for x in response.json()["results"]]
    assert str(ci_img.id) not in ids
    assert str(ci_img_2.id) in ids
    assert str(ci_json.id) not in ids

    rs = ReaderStudyFactory()
    ds = DisplaySetFactory(reader_study=rs)
    civ = ComponentInterfaceValueFactory(interface=ci_img)
    ds.values.add(civ)

    response = get_view_for_user(
        client=client,
        viewname="components:component-interface-autocomplete",
        user=user,
        data={
            "forward": json.dumps(
                {"object": rs.slug, "model": ReaderStudy._meta.model_name}
            )
        },
    )
    assert response.status_code == 200
    ids = [x["id"] for x in response.json()["results"]]
    assert str(ci_img.id) not in ids
    assert str(ci_img_2.id) in ids
    assert str(ci_json.id) in ids

    response = get_view_for_user(
        client=client,
        viewname="components:component-interface-autocomplete",
        user=user,
        data={
            "forward": json.dumps(
                {
                    "object": rs.slug,
                    "model": ReaderStudy._meta.model_name,
                    "interface-0": ci_img_2.pk,
                }
            )
        },
    )
    assert response.status_code == 200
    ids = [x["id"] for x in response.json()["results"]]
    assert str(ci_img.id) not in ids
    assert str(ci_img_2.id) not in ids
    assert str(ci_json.id) in ids


@pytest.mark.parametrize(
    "base_object_factory,base_obj_lookup,object_factory,view_with_object,view_without_object",
    (
        (
            ReaderStudyFactory,
            "reader_study",
            DisplaySetFactory,
            "reader-studies:display-set-interfaces-create",
            "reader-studies:display-set-new-interfaces-create",
        ),
        (
            ArchiveFactory,
            "archive",
            ArchiveItemFactory,
            "archives:item-interface-create",
            "archives:item-new-interface-create",
        ),
    ),
)
@pytest.mark.django_db
def test_interfaces_create_permissions(
    client,
    base_object_factory,
    base_obj_lookup,
    object_factory,
    view_with_object,
    view_without_object,
):
    editor, user = UserFactory.create_batch(2)
    base_obj = base_object_factory()
    obj = object_factory(**{base_obj_lookup: base_obj})
    base_obj.add_editor(editor)

    response = get_view_for_user(
        viewname=view_with_object,
        client=client,
        reverse_kwargs={"pk": obj.pk, "slug": base_obj.slug},
        user=user,
    )
    assert response.status_code == 403

    response = get_view_for_user(
        viewname=view_with_object,
        client=client,
        reverse_kwargs={"pk": obj.pk, "slug": base_obj.slug},
        user=editor,
    )
    assert response.status_code == 200

    response = get_view_for_user(
        viewname=view_without_object,
        client=client,
        reverse_kwargs={"slug": base_obj.slug},
        user=user,
    )
    assert response.status_code == 403

    response = get_view_for_user(
        viewname=view_without_object,
        client=client,
        reverse_kwargs={"slug": base_obj.slug},
        user=editor,
    )
    assert response.status_code == 200


@pytest.mark.parametrize(
    "base_object_factory,base_obj_lookup,object_factory,viewname,add_collaborator_attr",
    (
        (
            ReaderStudyFactory,
            "reader_study",
            DisplaySetFactory,
            "reader-studies:display-set-delete",
            "add_reader",
        ),
        (
            ArchiveFactory,
            "archive",
            ArchiveItemFactory,
            "archives:item-delete",
            "add_uploader",
        ),
    ),
)
@pytest.mark.django_db
def test_civset_delete_view(
    client,
    base_object_factory,
    base_obj_lookup,
    object_factory,
    viewname,
    add_collaborator_attr,
):
    user, editor, collaborator = UserFactory.create_batch(3)
    base_obj = base_object_factory()
    obj = object_factory(**{base_obj_lookup: base_obj})
    base_obj.add_editor(editor)
    setattr(base_obj, add_collaborator_attr, collaborator)

    response = get_view_for_user(
        viewname=viewname,
        client=client,
        user=user,
        reverse_kwargs={"slug": base_obj.slug, "pk": obj.pk},
    )
    assert response.status_code == 403

    response = get_view_for_user(
        viewname=viewname,
        client=client,
        user=collaborator,
        reverse_kwargs={"slug": base_obj.slug, "pk": obj.pk},
    )
    assert response.status_code == 403

    response = get_view_for_user(
        viewname=viewname,
        client=client,
        user=editor,
        reverse_kwargs={"slug": base_obj.slug, "pk": obj.pk},
    )
    assert response.status_code == 200

    response = get_view_for_user(
        viewname=viewname,
        client=client,
        method=client.post,
        user=editor,
        reverse_kwargs={"slug": base_obj.slug, "pk": obj.pk},
    )
    assert response.status_code == 302
    assert ArchiveItem.objects.count() == 0
    assert DisplaySet.objects.count() == 0
