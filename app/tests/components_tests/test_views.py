import json

import factory.django
import pytest
from django.conf import settings
from django.utils.html import format_html
from factory.fuzzy import FuzzyChoice

from grandchallenge.archives.models import ArchiveItem
from grandchallenge.components.form_fields import INTERFACE_FORM_FIELD_PREFIX
from grandchallenge.components.models import (
    InterfaceKind,
    InterfaceKindChoices,
)
from grandchallenge.components.widgets import FileWidgetChoices
from grandchallenge.reader_studies.models import DisplaySet, ReaderStudy
from grandchallenge.subdomains.utils import reverse
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmJobFactory,
)
from tests.archives_tests.factories import ArchiveFactory, ArchiveItemFactory
from tests.components_tests.factories import (
    ComponentInterfaceExampleValueFactory,
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.factories import UserFactory
from tests.reader_studies_tests.factories import (
    DisplaySetFactory,
    ReaderStudyFactory,
)
from tests.uploads_tests.factories import UserUploadFactory
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


@pytest.mark.django_db
@pytest.mark.parametrize(
    "object_factory, viewname, interface_list_viewname",
    [
        [
            ReaderStudyFactory,
            "reader-studies:display-set-new-interfaces-create",
            "components:component-interface-list-reader-studies",
        ],
        [
            ArchiveFactory,
            "archives:item-new-interface-create",
            "components:component-interface-list-archives",
        ],
    ],
)
def test_interfaces_list_link_in_new_interface_form(
    client, object_factory, viewname, interface_list_viewname
):
    object = object_factory()
    u = UserFactory()
    object.add_editor(u)

    response = get_view_for_user(
        viewname=viewname,
        client=client,
        method=client.get,
        reverse_kwargs={
            "slug": object.slug,
        },
        user=u,
    )
    assert reverse(interface_list_viewname) in response.rendered_content


@pytest.mark.django_db
def test_file_widget_select_view(client):
    user = UserFactory()
    ci = ComponentInterfaceFactory(
        kind=FuzzyChoice(InterfaceKind.interface_type_file())
    )
    response = get_view_for_user(
        viewname="components:file-widget-select",
        client=client,
        user=user,
        data={
            f"widget-choice-{ci.slug}": FileWidgetChoices.FILE_SEARCH.name,
            "prefixed-interface-slug": ci.slug,
        },
    )
    assert '<input class="form-control" type="search"' in str(response.content)

    response2 = get_view_for_user(
        viewname="components:file-widget-select",
        client=client,
        user=user,
        data={
            f"widget-choice-{ci.slug}": FileWidgetChoices.FILE_UPLOAD.name,
            "prefixed-interface-slug": ci.slug,
        },
    )
    assert 'class="user-upload"' in str(response2.content)

    response3 = get_view_for_user(
        viewname="components:file-widget-select",
        client=client,
        user=user,
        data={
            f"widget-choice-{ci.slug}": FileWidgetChoices.UNDEFINED.name,
            "prefixed-interface-slug": ci.slug,
        },
    )
    assert response3.content == b""

    civ = ComponentInterfaceValueFactory(interface=ci)
    response4 = get_view_for_user(
        viewname="components:file-widget-select",
        client=client,
        user=user,
        data={
            f"widget-choice-{ci.slug}": FileWidgetChoices.FILE_SELECTED.name,
            "prefixed-interface-slug": ci.slug,
            "current-value": civ.pk,
        },
    )
    assert format_html(
        '<input type="hidden" name="{}" value="{}">', ci.slug, civ.pk
    ) in str(response4.content)

    user_upload = UserUploadFactory()
    response5 = get_view_for_user(
        viewname="components:file-widget-select",
        client=client,
        user=user,
        data={
            f"widget-choice-{ci.slug}": FileWidgetChoices.FILE_SELECTED.name,
            "prefixed-interface-slug": ci.slug,
            "current-value": user_upload.pk,
        },
    )
    assert format_html(
        '<input type="hidden" name="{}" value="{}">', ci.slug, user_upload.pk
    ) in str(response5.content)

    civ_pk = civ.pk
    civ.delete()
    response6 = get_view_for_user(
        viewname="components:file-widget-select",
        client=client,
        user=user,
        data={
            f"widget-choice-{ci.slug}": FileWidgetChoices.FILE_SELECTED.name,
            "prefixed-interface-slug": ci.slug,
            "current-value": civ_pk,
        },
    )
    assert response6.status_code == 404

    response7 = get_view_for_user(
        viewname="components:file-widget-select",
        client=client,
        user=user,
        data={
            f"widget-choice-{ci.slug}": FileWidgetChoices.FILE_SEARCH.name
            + "foobar",
            "prefixed-interface-slug": ci.slug,
        },
    )
    assert response7.status_code == 404

    ci_slug = ci.slug
    ci.delete()
    response8 = get_view_for_user(
        viewname="components:file-widget-select",
        client=client,
        user=user,
        data={
            f"widget-choice-{ci_slug}": FileWidgetChoices.FILE_SEARCH.name,
            "prefixed-interface-slug": ci_slug,
        },
    )
    assert response8.status_code == 404


@pytest.mark.django_db
def test_file_search_result_view_no_file_access(client):
    user = UserFactory()
    ci = ComponentInterfaceFactory(
        kind=FuzzyChoice(InterfaceKind.interface_type_file())
    )
    response = get_view_for_user(
        viewname="components:file-search",
        client=client,
        method=client.get,
        data={
            "prefixed-interface-slug": f"{INTERFACE_FORM_FIELD_PREFIX}{ci.slug}",
        },
        user=user,
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_file_search_result_view_no_files(client):
    user = UserFactory()
    algorithm = AlgorithmFactory()
    algorithm.add_editor(user)
    ci = ComponentInterfaceFactory(
        kind=FuzzyChoice(InterfaceKind.interface_type_file())
    )
    response = get_view_for_user(
        viewname="components:file-search",
        client=client,
        method=client.get,
        data={
            "prefixed-interface-slug": f"{INTERFACE_FORM_FIELD_PREFIX}{ci.slug}",
        },
        user=user,
    )
    assert response.status_code == 200
    assert ci.slug in response.rendered_content
    assert "No files match your search criteria." in response.rendered_content


@pytest.mark.django_db
def test_file_search_result_view(client):
    user = UserFactory()
    algorithm = AlgorithmFactory()
    algorithm.add_editor(user)
    ci = ComponentInterfaceFactory()
    civ = ComponentInterfaceValueFactory(
        interface=ci, file=factory.django.FileField()
    )

    response = get_view_for_user(
        viewname="components:file-search",
        client=client,
        method=client.get,
        data={
            "prefixed-interface-slug": f"{INTERFACE_FORM_FIELD_PREFIX}{ci.slug}",
        },
        user=user,
    )

    assert response.status_code == 200
    assert ci.slug in response.rendered_content
    assert "No files match your search criteria." in response.rendered_content

    job = AlgorithmJobFactory(creator=user, time_limit=60)
    job.inputs.set([civ])

    response = get_view_for_user(
        viewname="components:file-search",
        client=client,
        method=client.get,
        data={
            "prefixed-interface-slug": f"{INTERFACE_FORM_FIELD_PREFIX}{ci.slug}",
        },
        user=user,
    )

    assert response.status_code == 200
    assert ci.slug in response.rendered_content
    assert f"{civ.title} ({civ.pk})" in response.rendered_content


@pytest.mark.django_db
def test_file_search_result_view_filter_by_pk(client):
    user = UserFactory()
    algorithm = AlgorithmFactory()
    algorithm.add_editor(user)
    ci = ComponentInterfaceFactory()
    civ1, civ2, civ3, civ4 = ComponentInterfaceValueFactory.create_batch(
        4,
        interface=ci,
        file=factory.django.FileField(),
    )
    job = AlgorithmJobFactory(creator=user, time_limit=60)
    job.inputs.set([civ1, civ2, civ3])

    response = get_view_for_user(
        viewname="components:file-search",
        client=client,
        method=client.get,
        data={
            "prefixed-interface-slug": f"{INTERFACE_FORM_FIELD_PREFIX}{ci.slug}",
        },
        user=user,
    )

    assert response.status_code == 200
    assert ci.slug in response.rendered_content
    assert f"{civ1.title} ({civ1.pk})" in response.rendered_content
    assert f"{civ2.title} ({civ2.pk})" in response.rendered_content
    assert f"{civ3.title} ({civ3.pk})" in response.rendered_content
    assert f"{civ4.title} ({civ4.pk})" not in response.rendered_content

    response = get_view_for_user(
        viewname="components:file-search",
        client=client,
        method=client.get,
        data={
            "prefixed-interface-slug": f"{INTERFACE_FORM_FIELD_PREFIX}{ci.slug}",
            f"query-{INTERFACE_FORM_FIELD_PREFIX}{ci.slug}": f"{civ1.pk}",
        },
        user=user,
    )

    assert response.status_code == 200
    assert ci.slug in response.rendered_content
    assert f"{civ1.title} ({civ1.pk})" in response.rendered_content
    assert f"{civ2.title} ({civ2.pk})" not in response.rendered_content
    assert f"{civ3.title} ({civ3.pk})" not in response.rendered_content
    assert f"{civ4.title} ({civ4.pk})" not in response.rendered_content


@pytest.mark.django_db
def test_file_search_result_view_filter_by_name(client):
    user = UserFactory()
    algorithm = AlgorithmFactory()
    algorithm.add_editor(user)
    ci = ComponentInterfaceFactory()
    civ1 = ComponentInterfaceValueFactory(
        interface=ci,
        file=factory.django.FileField(filename="foobar1.dat"),
    )
    civ2 = ComponentInterfaceValueFactory(
        interface=ci,
        file=factory.django.FileField(filename="foobar2.dat"),
    )
    civ3 = ComponentInterfaceValueFactory(
        interface=ci,
        file=factory.django.FileField(filename="foobaz.dat"),
    )
    job = AlgorithmJobFactory(creator=user, time_limit=60)
    job.inputs.set([civ1, civ2, civ3])

    response = get_view_for_user(
        viewname="components:file-search",
        client=client,
        method=client.get,
        data={
            "prefixed-interface-slug": f"{INTERFACE_FORM_FIELD_PREFIX}{ci.slug}",
        },
        user=user,
    )

    assert response.status_code == 200
    assert ci.slug in response.rendered_content
    assert f"{civ1.title} ({civ1.pk})" in response.rendered_content
    assert f"{civ2.title} ({civ2.pk})" in response.rendered_content
    assert f"{civ3.title} ({civ3.pk})" in response.rendered_content

    response = get_view_for_user(
        viewname="components:file-search",
        client=client,
        method=client.get,
        data={
            "prefixed-interface-slug": f"{INTERFACE_FORM_FIELD_PREFIX}{ci.slug}",
            f"query-{INTERFACE_FORM_FIELD_PREFIX}{ci.slug}": "foobar",
        },
        user=user,
    )

    assert response.status_code == 200
    assert ci.slug in response.rendered_content
    assert f"{civ1.title} ({civ1.pk})" in response.rendered_content
    assert f"{civ2.title} ({civ2.pk})" in response.rendered_content
    assert f"{civ3.title} ({civ3.pk})" not in response.rendered_content
