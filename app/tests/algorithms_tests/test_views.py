import pytest

from django.utils.text import slugify

from grandchallenge.subdomains.utils import reverse
from grandchallenge.algorithms.models import AlgorithmImage

from tests.algorithms_tests.factories import AlgorithmImageFactory
from tests.factories import UserFactory, StagedFileFactory
from tests.utils import get_view_for_user, get_temporary_image


@pytest.mark.django_db
def test_algorithm_list_view(client):
    ai1, ai2 = AlgorithmImageFactory(), AlgorithmImageFactory()
    user = UserFactory(is_staff=True)

    response = get_view_for_user(
        viewname="algorithms:image-list", client=client, user=user
    )

    assert ai1.get_absolute_url() in response.rendered_content
    assert ai2.get_absolute_url() in response.rendered_content

    ai1.delete()

    response = get_view_for_user(
        viewname="algorithms:image-list", client=client, user=user
    )

    assert ai1.get_absolute_url() not in response.rendered_content
    assert ai2.get_absolute_url() in response.rendered_content


@pytest.mark.django_db
def test_algorithm_create_detail(client):
    user = UserFactory(is_staff=True)

    title = "Test algorithm"
    description = "Description of test algorithm"
    algorithm_image = StagedFileFactory(file__filename="test_image.tar.gz")
    response = get_view_for_user(
        client=client, viewname="algorithms:image-create", user=user
    )
    assert response.status_code == 200

    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="algorithms:image-create",
        user=user,
        data={
            "title": title,
            "description": description,
            "logo": get_temporary_image(),
            "chunked_upload": algorithm_image.file_id,
        },
    )
    assert response.status_code == 302
    assert response.url == reverse(
        "algorithms:image-detail", kwargs={"slug": slugify(title)}
    )

    ai = AlgorithmImage.objects.get(title=title)
    assert ai.title == title
    assert ai.description == description

    response = get_view_for_user(url=response.url, client=client, user=user)
    assert title in response.rendered_content
    assert description in response.rendered_content


@pytest.mark.django_db
def test_algorithm_run(client):
    user = UserFactory(is_staff=True)
    ai1 = AlgorithmImageFactory()
    response = get_view_for_user(
        viewname="algorithms:execution-session-create",
        reverse_kwargs={"slug": slugify(ai1.title)},
        client=client,
        user=user,
    )
    assert response.status_code == 200
