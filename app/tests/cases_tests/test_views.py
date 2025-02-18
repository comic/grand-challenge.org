import pytest
from django.utils.html import format_html
from guardian.shortcuts import assign_perm, remove_perm

from grandchallenge.cases.widgets import ImageWidgetChoices
from grandchallenge.components.models import ComponentInterface
from tests.cases_tests.factories import RawImageUploadSessionFactory
from tests.components_tests.factories import ComponentInterfaceFactory
from tests.factories import ImageFactory, UserFactory
from tests.uploads_tests.factories import UserUploadFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
class TestObjectPermissionRequiredViews:
    def test_permission_required_views(self, client):
        rius = RawImageUploadSessionFactory()
        u = UserFactory()

        for view_name, kwargs, permission, obj in [
            (
                "raw-image-upload-session-detail",
                {"pk": rius.pk},
                "view_rawimageuploadsession",
                rius,
            ),
        ]:
            response = get_view_for_user(
                client=client,
                viewname=f"cases:{view_name}",
                reverse_kwargs=kwargs,
                user=u,
            )

            assert response.status_code == 403

            assign_perm(permission, u, obj)

            response = get_view_for_user(
                client=client,
                viewname=f"cases:{view_name}",
                reverse_kwargs=kwargs,
                user=u,
            )

            assert response.status_code == 200

            remove_perm(permission, u, obj)

    def test_permission_filtered_views(self, client):
        rius = RawImageUploadSessionFactory()
        u = UserFactory()

        for view_name, kwargs, permission, obj in [
            (
                "raw-image-upload-session-list",
                {},
                "view_rawimageuploadsession",
                rius,
            )
        ]:
            assign_perm(permission, u, obj)

            response = get_view_for_user(
                client=client,
                viewname=f"cases:{view_name}",
                reverse_kwargs=kwargs,
                user=u,
            )

            assert response.status_code == 200
            assert obj in response.context[-1]["object_list"]

            remove_perm(permission, u, obj)

            response = get_view_for_user(
                client=client,
                viewname=f"cases:{view_name}",
                reverse_kwargs=kwargs,
                user=u,
            )

            assert response.status_code == 200
            assert obj not in response.context[-1]["object_list"]


P = "patient_id__isempty"
S = "study_description__isempty"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "factory_kwargs,data_non_filtered,data_filtered",
    (
        (
            {},
            ({}, {P: True}, {S: True}, {P: True, S: True}),
            ({P: False}, {S: False}, {P: False, S: False}),
        ),
        (
            {"patient_id": "test"},
            ({}, {P: False}, {S: True}, {P: False, S: True}),
            ({P: True}, {S: False}, {P: True, S: False}),
        ),
        (
            {"study_description": "test"},
            ({}, {P: True}, {S: False}, {P: True, S: False}),
            ({P: False}, {S: True}, {P: False, S: True}),
        ),
        (
            {"study_description": "test", "patient_id": "test"},
            ({}, {P: False}, {S: False}, {P: False, S: False}),
            ({P: True}, {S: True}, {P: True, S: True}),
        ),
    ),
)
def test_imageviewset_empty_fields_filtering(
    client, factory_kwargs, data_non_filtered, data_filtered
):
    image = ImageFactory(**factory_kwargs)
    u = UserFactory()
    assign_perm("view_image", u, image)
    view_kwargs = {"client": client, "viewname": "api:image-list", "user": u}
    for data in data_non_filtered:
        response = get_view_for_user(**view_kwargs, data=data)
        assert response.status_code == 200
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["pk"] == str(image.pk)

    for data in data_filtered:
        response = get_view_for_user(**view_kwargs, data=data)
        assert response.status_code == 200
        assert len(response.data["results"]) == 0


@pytest.mark.django_db
def test_image_search_view(client):
    user = UserFactory()
    im1, im2, im3 = ImageFactory.create_batch(3)
    assign_perm("cases.view_image", user, im1)
    assign_perm("cases.view_image", user, im2)
    im2.name = "test.mha"
    im2.save()
    ci = ComponentInterfaceFactory(kind=ComponentInterface.Kind.IMAGE)

    response = get_view_for_user(
        viewname="cases:image-search",
        client=client,
        user=user,
        data={
            "prefixed-interface-slug": ci.slug,
            f"query-{ci.slug}": "test",
        },
    )
    assert response.status_code == 200
    assert len(response.context_data["object_list"]) == 1
    assert response.context_data["object_list"].get() == im2

    response = get_view_for_user(
        viewname="cases:image-search",
        client=client,
        user=user,
        data={
            "prefixed-interface-slug": ci.slug,
            f"query-{ci.slug}": "",
        },
    )
    assert response.status_code == 200
    assert len(response.context_data["object_list"]) == 2
    assert im1 in response.context_data["object_list"].all()
    assert im2 in response.context_data["object_list"].all()
    assert im3 not in response.context_data["object_list"].all()


@pytest.mark.django_db
def test_image_widget_select_view(client):
    user = UserFactory()
    ci = ComponentInterfaceFactory(kind=ComponentInterface.Kind.IMAGE)
    response = get_view_for_user(
        viewname="cases:select-image-widget",
        client=client,
        user=user,
        data={
            f"widget-choice-{ci.slug}": ImageWidgetChoices.IMAGE_SEARCH.name,
            "prefixed-interface-slug": ci.slug,
        },
    )
    assert '<input class="form-control" type="search"' in str(response.content)

    response2 = get_view_for_user(
        viewname="cases:select-image-widget",
        client=client,
        user=user,
        data={
            f"widget-choice-{ci.slug}": ImageWidgetChoices.IMAGE_UPLOAD.name,
            "prefixed-interface-slug": ci.slug,
        },
    )
    assert 'class="user-upload"' in str(response2.content)

    response3 = get_view_for_user(
        viewname="cases:select-image-widget",
        client=client,
        user=user,
        data={
            f"widget-choice-{ci.slug}": ImageWidgetChoices.UNDEFINED.name,
            "prefixed-interface-slug": ci.slug,
        },
    )
    assert response3.content == b""

    image = ImageFactory()
    response4 = get_view_for_user(
        viewname="cases:select-image-widget",
        client=client,
        user=user,
        data={
            f"widget-choice-{ci.slug}": ImageWidgetChoices.IMAGE_SELECTED.name,
            "prefixed-interface-slug": ci.slug,
            "current-value": image.pk,
        },
    )
    assert format_html(
        '<input type="hidden" name="{}" value="{}">', ci.slug, image.pk
    ) in str(response4.content)

    user_upload = UserUploadFactory()
    response5 = get_view_for_user(
        viewname="cases:select-image-widget",
        client=client,
        user=user,
        data={
            f"widget-choice-{ci.slug}": ImageWidgetChoices.IMAGE_SELECTED.name,
            "prefixed-interface-slug": ci.slug,
            "current-value": user_upload.pk,
        },
    )
    assert format_html(
        '<input type="hidden" name="{}" value="{}">', ci.slug, user_upload.pk
    ) in str(response5.content)
