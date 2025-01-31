import pytest
from django.utils.html import format_html
from factory.fuzzy import FuzzyChoice

from grandchallenge.components.models import InterfaceKind
from grandchallenge.components.widgets import FileWidgetChoices
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.factories import UserFactory
from tests.uploads_tests.factories import UserUploadFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_flexible_file_widget(client):
    user = UserFactory()
    ci = ComponentInterfaceFactory(
        kind=FuzzyChoice(InterfaceKind.interface_type_file())
    )
    response = get_view_for_user(
        viewname="components:select-file-widget",
        client=client,
        user=user,
        data={
            f"widget-choice-{ci.slug}": FileWidgetChoices.FILE_SEARCH.name,
            "prefixed-interface-slug": ci.slug,
        },
    )
    assert '<input class="form-control" type="search"' in str(response.content)

    response2 = get_view_for_user(
        viewname="components:select-file-widget",
        client=client,
        user=user,
        data={
            f"widget-choice-{ci.slug}": FileWidgetChoices.FILE_UPLOAD.name,
            "prefixed-interface-slug": ci.slug,
        },
    )
    assert 'class="user-upload"' in str(response2.content)

    response3 = get_view_for_user(
        viewname="components:select-file-widget",
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
        viewname="components:select-file-widget",
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
        viewname="components:select-file-widget",
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
        viewname="components:select-file-widget",
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
        viewname="components:select-file-widget",
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
        viewname="components:select-file-widget",
        client=client,
        user=user,
        data={
            f"widget-choice-{ci_slug}": FileWidgetChoices.FILE_SEARCH.name,
            "prefixed-interface-slug": ci_slug,
        },
    )
    assert response8.status_code == 404
