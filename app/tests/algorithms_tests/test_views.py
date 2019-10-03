import pytest

from django.utils.text import slugify

from grandchallenge.subdomains.utils import reverse
from grandchallenge.algorithms.models import AlgorithmImage, Algorithm

from tests.algorithms_tests.factories import (
    AlgorithmImageFactory,
    AlgorithmFactory,
)
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
    algorithm = AlgorithmFactory()

    algorithm_image = StagedFileFactory(file__filename="test_image.tar.gz")
    response = get_view_for_user(
        client=client,
        viewname="algorithms:image-create",
        reverse_kwargs={"slug": algorithm.slug},
        user=user,
    )
    assert response.status_code == 200

    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="algorithms:image-create",
        reverse_kwargs={"slug": algorithm.slug},
        user=user,
        data={"chunked_upload": algorithm_image.file_id},
    )
    assert response.status_code == 302
    assert response.url == reverse(
        "algorithms:image-detail", kwargs={"slug": algorithm.slug}
    )

    # TODO: test that the algorithm is correctly set


@pytest.mark.django_db
def test_algorithm_run(client):
    user = UserFactory(is_staff=True)
    ai1 = AlgorithmImageFactory()
    response = get_view_for_user(
        viewname="algorithms:execution-session-create",
        reverse_kwargs={"slug": slugify(ai1.algorithm.slug)},
        client=client,
        user=user,
    )
    assert response.status_code == 200
