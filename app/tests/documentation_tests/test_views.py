import pytest
from django.core.exceptions import MultipleObjectsReturned
from guardian.shortcuts import assign_perm

from grandchallenge.documentation.models import DocPage
from tests.documentation_tests.factories import DocPageFactory
from tests.factories import UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
@pytest.mark.parametrize(
    "view, perm",
    [
        ("documentation:create", "documentation.add_docpage"),
        ("documentation:content-update", "documentation.change_docpage"),
        ("documentation:metadata-update", "documentation.change_docpage"),
    ],
)
def test_permissions(client, view, perm):
    u1 = UserFactory()
    p1 = DocPageFactory()

    if view in (
        "documentation:content-update",
        "documentation:metadata-update",
    ):
        reverse_kwargs = {"slug": p1.slug}
    else:
        reverse_kwargs = None

    response = get_view_for_user(
        viewname=view, client=client, reverse_kwargs=reverse_kwargs, user=u1
    )
    assert response.status_code == 403

    # give user permission
    assign_perm(perm, u1)

    response = get_view_for_user(
        viewname=view, client=client, reverse_kwargs=reverse_kwargs, user=u1
    )
    assert response.status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize("is_faq", (True, False))
def test_docpage_create(client, is_faq):
    u1 = UserFactory()
    assign_perm("documentation.add_docpage", u1)
    assign_perm("documentation.change_docpage", u1)

    content = "<h1>Example content</h1>"
    title = "Test title"

    response = get_view_for_user(
        viewname="documentation:create",
        client=client,
        method=client.post,
        data={"title": title, "is_faq": is_faq},
        user=u1,
    )

    assert response.status_code == 302
    assert DocPage.objects.count() == 1
    assert response.url.endswith("test-title/content-update/")
    response = get_view_for_user(
        url=response.url,
        client=client,
        method=client.post,
        data={"content": content},
        user=u1,
    )
    assert response.status_code == 302

    response = get_view_for_user(url=response.url, client=client)

    assert response.status_code == 200
    assert content in str(response.content)


@pytest.mark.django_db
@pytest.mark.parametrize("is_faq", (True, False))
def test_docpage_content_update(client, is_faq):
    u1 = UserFactory()
    p = DocPageFactory(is_faq=is_faq)
    assign_perm("documentation.change_docpage", u1)

    new_content = "<h1>New content</h1>"

    # change content of p
    response = get_view_for_user(
        viewname="documentation:content-update",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": p.slug},
        data={"content": new_content},
        user=u1,
    )

    assert response.status_code == 302
    p.refresh_from_db()
    assert p.content == new_content


@pytest.mark.django_db
def test_docpage_position_update(client):
    u1 = UserFactory()
    _ = DocPageFactory()
    p2 = DocPageFactory()
    assign_perm("documentation.change_docpage", u1)

    assert p2.order == 2

    # change order of p2
    response = get_view_for_user(
        viewname="documentation:metadata-update",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": p2.slug},
        data={"title": p2.title, "position": 1},
        user=u1,
    )

    assert response.status_code == 302
    p2.refresh_from_db()
    assert p2.order == 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    "query, target_pages",
    [
        ("algorithm", [0]),
        ("algoritm", [0]),
        ("alg", [0]),
        ("study", [1]),
        ("content", [0, 1]),
    ],
)
def test_search(client, query, target_pages):
    u1 = UserFactory()
    p1 = DocPageFactory(
        title="algorithms", content="some content about algorithms"
    )
    p2 = DocPageFactory(
        title="reader studies", content="some content about reader studies"
    )
    pages = [p1, p2]

    matching_pages = []
    if len(target_pages) > 1:
        for _ in target_pages:
            matching_pages.append(pages.pop(0))
    else:
        matching_pages = pages.pop(target_pages[0])

    non_matching_pages = pages

    assign_perm("documentation.change_docpage", u1)

    response = get_view_for_user(
        viewname="documentation:home",
        client=client,
        data={"query": query},
        user=u1,
    )

    try:
        assert response.context_data["search_results"].get() == matching_pages
    except MultipleObjectsReturned:
        for match in response.context_data["search_results"].all():
            assert match in matching_pages

    if non_matching_pages:
        assert (
            response.context_data["search_results"].get()
            not in non_matching_pages
        )


@pytest.fixture
def nested_docpages():
    page = None
    pages = []
    for _ in range(4):
        page = DocPageFactory(parent=page)
        pages.append(page)
    return pages


@pytest.mark.django_db
@pytest.mark.flaky(reruns=3)
@pytest.mark.parametrize(
    "level, num_queries",
    (
        (0, 40),
        (1, 41),  # +1 parent is not null
        (2, 42),  # +1 parent breadcrumb
        (3, 43),  # +1 parent breadcrumb
    ),
)
def test_docpage_detail_num_queries(
    client, django_assert_num_queries, nested_docpages, level, num_queries
):
    user = UserFactory()
    page = nested_docpages[level]

    with django_assert_num_queries(num_queries) as _:
        response = get_view_for_user(
            viewname="documentation:detail",
            reverse_kwargs={"slug": page.slug},
            client=client,
            method=client.get,
            user=user,
        )
        # Sanity checks
        assert response.status_code == 200
        assert page.content in response.content.decode("utf-8")


@pytest.mark.django_db
def test_docpage_detail_filter_top_level_pages_on_is_faq(client):
    user = UserFactory()
    docpage = DocPageFactory()
    faqpage = DocPageFactory(is_faq=True)

    response = get_view_for_user(
        viewname="documentation:detail",
        reverse_kwargs={"slug": docpage.slug},
        client=client,
        method=client.get,
        user=user,
    )
    assert response.status_code == 200
    assert docpage in response.context["top_level_pages"]
    assert faqpage not in response.context["top_level_pages"]

    response = get_view_for_user(
        viewname="documentation:detail",
        reverse_kwargs={"slug": faqpage.slug},
        client=client,
        method=client.get,
        user=user,
    )
    assert response.status_code == 200
    assert docpage not in response.context["top_level_pages"]
    assert faqpage in response.context["top_level_pages"]


@pytest.mark.django_db
def test_docpage_detail_faq_navigation_pane(client):
    user = UserFactory()
    docpage = DocPageFactory()
    faq_homepage = DocPageFactory(title="FAQ", is_faq=True)
    faq_category_page = DocPageFactory(
        title="Challenges",
        is_faq=True,
        parent=faq_homepage,
    )
    faq_page = DocPageFactory(
        is_faq=True,
        parent=faq_category_page,
    )
    faq_pages = [faq_homepage, faq_category_page, faq_page]

    response = get_view_for_user(
        viewname="documentation:detail",
        reverse_kwargs={"slug": docpage.slug},
        client=client,
        method=client.get,
        user=user,
    )
    assert response.status_code == 200
    # nav button to doc page is shown
    assert f'href="/documentation/{docpage.slug}/"' in str(
        response.rendered_content
    )
    # nav button to faq page is NOT shown
    assert f'href="/documentation/{faq_page.slug}/"' not in str(
        response.rendered_content
    )

    response = get_view_for_user(
        viewname="documentation:detail",
        reverse_kwargs={"slug": faq_page.slug},
        client=client,
        method=client.get,
        user=user,
    )
    assert response.status_code == 200
    # nav button to doc page is NOT shown
    assert f'href="/documentation/{docpage.slug}/"' not in str(
        response.rendered_content
    )
    # nav buttons to faq pages are shown
    for fp in faq_pages:
        assert f'href="/documentation/{fp.slug}/"' in str(
            response.rendered_content
        )
