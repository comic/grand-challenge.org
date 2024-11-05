import json

import pytest
from django.conf import settings

from grandchallenge.archives.models import ArchiveItem
from grandchallenge.components.models import (
    ComponentInterface,
    InterfaceKindChoices,
)
from grandchallenge.reader_studies.models import DisplaySet, ReaderStudy
from tests.algorithms_tests.factories import AlgorithmFactory
from tests.archives_tests.factories import ArchiveFactory, ArchiveItemFactory
from tests.components_tests.factories import (
    ComponentInterfaceExampleValueFactory,
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.conftest import get_interface_form_data
from tests.factories import ImageFactory, UserFactory
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
    method = getattr(base_obj, add_collaborator_attr)
    setattr(base_obj, add_collaborator_attr, method)
    getattr(base_obj, add_collaborator_attr)(collaborator)

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


@pytest.mark.parametrize(
    "base_object_factory,base_obj_lookup,object_factory,viewname,add_collaborator_attr,collaborator_visible_obj_count",
    (
        (
            ReaderStudyFactory,
            "reader_study",
            DisplaySetFactory,
            "reader-studies:display_sets",
            "add_reader",
            0,
        ),
        (
            ArchiveFactory,
            "archive",
            ArchiveItemFactory,
            "archives:items-list",
            "add_uploader",
            3,
        ),
        (
            ArchiveFactory,
            "archive",
            ArchiveItemFactory,
            "archives:items-list",
            "add_user",
            3,
        ),
    ),
)
@pytest.mark.django_db
def test_civset_list_view_permissions(
    client,
    base_object_factory,
    base_obj_lookup,
    object_factory,
    viewname,
    add_collaborator_attr,
    collaborator_visible_obj_count,
):
    user, editor, collaborator = UserFactory.create_batch(3)
    base_obj = base_object_factory()
    base_obj.add_editor(editor)
    method = getattr(base_obj, add_collaborator_attr)
    setattr(base_obj, add_collaborator_attr, method)
    getattr(base_obj, add_collaborator_attr)(collaborator)
    ob1, ob2, ob3 = object_factory.create_batch(
        3, **{base_obj_lookup: base_obj}
    )
    ob4, ob5 = object_factory.create_batch(2)

    response = get_view_for_user(
        viewname=viewname,
        client=client,
        user=user,
        reverse_kwargs={"slug": base_obj.slug},
    )
    assert response.status_code == 200
    assert len(response.context["object_list"]) == 0

    response = get_view_for_user(
        viewname=viewname,
        client=client,
        user=collaborator,
        reverse_kwargs={"slug": base_obj.slug},
    )
    assert response.status_code == 200
    assert (
        len(response.context["object_list"]) == collaborator_visible_obj_count
    )

    response = get_view_for_user(
        viewname=viewname,
        client=client,
        user=editor,
        reverse_kwargs={"slug": base_obj.slug},
    )
    assert response.status_code == 200
    assert len(response.context["object_list"]) == 3
    for obj in [ob1, ob2, ob3]:
        assert obj in response.context["object_list"]
    for obj in [ob4, ob5]:
        assert obj not in response.context["object_list"]


@pytest.mark.parametrize(
    "base_object_factory,base_obj_lookup,object_factory,viewname",
    (
        (
            ReaderStudyFactory,
            "reader_study",
            DisplaySetFactory,
            "reader-studies:display-sets-bulk-delete",
        ),
        (
            ArchiveFactory,
            "archive",
            ArchiveItemFactory,
            "archives:items-bulk-delete",
        ),
    ),
)
@pytest.mark.django_db
def test_display_set_bulk_delete_confirmation_page(
    client, base_object_factory, base_obj_lookup, object_factory, viewname
):
    editor = UserFactory()
    base_obj = base_object_factory()
    base_obj.add_editor(editor)

    ob1, ob2, ob3, ob4, ob5 = object_factory.create_batch(
        5, **{base_obj_lookup: base_obj}
    )
    response = get_view_for_user(
        client=client,
        viewname=viewname,
        reverse_kwargs={"slug": base_obj.slug},
        user=editor,
        data={"selected-for-deletion": ob1.pk},
    )
    assert response.status_code == 200
    assert "Are you sure you want to delete the following 1 " in str(
        response.content
    )

    response = get_view_for_user(
        client=client,
        viewname=viewname,
        reverse_kwargs={"slug": base_obj.slug},
        user=editor,
        data={"delete-all": True},
    )
    assert response.status_code == 200
    assert "Are you sure you want to delete the following 5 " in str(
        response.content
    )


@pytest.mark.parametrize(
    "base_object_factory,base_obj_lookup,object_factory,viewname",
    (
        (
            ReaderStudyFactory,
            "reader_study",
            DisplaySetFactory,
            "reader-studies:display-sets-bulk-delete",
        ),
        (
            ArchiveFactory,
            "archive",
            ArchiveItemFactory,
            "archives:items-bulk-delete",
        ),
    ),
)
@pytest.mark.django_db
def test_display_set_bulk_delete(
    client, base_object_factory, base_obj_lookup, object_factory, viewname
):
    editor = UserFactory()
    base_obj = base_object_factory()
    base_obj.add_editor(editor)

    ob1, ob2, ob3, ob4, ob5 = object_factory.create_batch(
        5, **{base_obj_lookup: base_obj}
    )
    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname=viewname,
        reverse_kwargs={"slug": base_obj.slug},
        user=editor,
        data={"civ_sets_to_delete": [ob1.pk, ob2.pk]},
    )
    assert response.status_code == 302
    assert base_obj.civ_sets_related_manager.count() == 3
    assert ob1 not in base_obj.civ_sets_related_manager.all()
    assert ob2 not in base_obj.civ_sets_related_manager.all()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "object",
    [
        ReaderStudyFactory,
        ArchiveFactory,
        AlgorithmFactory,
    ],
)
def test_file_upload_form_field_view(client, object):
    object = object()
    u, editor = UserFactory.create_batch(2)
    object.add_editor(editor)

    ci_json = ComponentInterfaceFactory(kind="JSON", store_in_database=False)

    response = get_view_for_user(
        viewname="components:file-upload",
        client=client,
        reverse_kwargs={
            "interface_slug": ci_json.slug,
        },
        user=u,
    )
    assert response.status_code == 403

    response = get_view_for_user(
        viewname="components:file-upload",
        client=client,
        reverse_kwargs={
            "interface_slug": ci_json.slug,
        },
        user=editor,
    )
    assert response.status_code == 200
    assert "user-upload" in str(response.content)


@pytest.mark.django_db
def test_display_ci_example_value(client):
    v = ComponentInterfaceExampleValueFactory(
        interface__kind=InterfaceKindChoices.STRING,
        value="EXAMPLE-VALUE-TEST-STRING",
        extra_info="EXAMPLE-EXTRA-INFO-TEST-STRING",
    )

    response = get_view_for_user(
        viewname="components:component-interface-list-input",
        client=client,
        method=client.get,
        user=UserFactory(),
    )

    assert response.status_code == 200
    assert v.value in response.rendered_content
    assert v.extra_info in response.rendered_content


@pytest.mark.parametrize(
    "base_object_factory,base_obj_lookup,object_factory,viewname",
    (
        (
            ReaderStudyFactory,
            "reader_study",
            DisplaySetFactory,
            "reader-studies:display-set-update",
        ),
        (
            ArchiveFactory,
            "archive",
            ArchiveItemFactory,
            "archives:item-edit",
        ),
    ),
)
@pytest.mark.django_db
def test_image_widget_populated_value_on_update_view_validation_error(
    client, base_object_factory, base_obj_lookup, object_factory, viewname
):
    image1 = ImageFactory()
    image_ci = ComponentInterfaceFactory(kind=ComponentInterface.Kind.IMAGE)
    image1_civ = ComponentInterfaceValueFactory(
        interface=image_ci, image=image1
    )

    annotation = "{}"
    annotation_ci = ComponentInterfaceFactory(
        kind=ComponentInterface.Kind.TWO_D_BOUNDING_BOX, title="annotation"
    )
    annotation_civ = ComponentInterfaceValueFactory(
        interface=annotation_ci, value=annotation
    )

    editor = UserFactory()
    base_obj = base_object_factory()
    base_obj.add_editor(editor)

    ob = object_factory(**{base_obj_lookup: base_obj})
    ob.values.set([image1_civ, annotation_civ])

    image2 = ImageFactory()
    data = {
        "interface_slug": image_ci.slug,
        "current_value": image2.pk,
    }
    data.update(
        **get_interface_form_data(interface_slug=image_ci.slug, data=image2.pk)
    )
    data.update(
        **get_interface_form_data(
            interface_slug=annotation_ci.slug, data='{"1":1}'
        )
    )

    response = get_view_for_user(
        client=client,
        viewname=viewname,
        reverse_kwargs={"slug": base_obj.slug, "pk": ob.pk},
        user=editor,
        method=client.post,
        follow=True,
        data=data,
    )
    assert response.status_code == 200
    assert f'<option value="IMAGE_SELECTED">{image2.title}</option>' in str(
        response.rendered_content
    )
