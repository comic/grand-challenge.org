import pytest
from django.conf import settings

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
        data={"forward": f'{{"reader-study": "{rs.slug}"}}'},
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
            "forward": f'{{"reader-study": "{rs.slug}", "interface-0": "{str(ci_img_2.pk)}"}}'
        },
    )
    assert response.status_code == 200
    ids = [x["id"] for x in response.json()["results"]]
    assert str(ci_img.id) not in ids
    assert str(ci_img_2.id) not in ids
    assert str(ci_json.id) in ids
