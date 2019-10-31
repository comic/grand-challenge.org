import pytest
from django.contrib.auth.models import Group
from django.utils.text import slugify

from grandchallenge.algorithms.models import AlgorithmImage
from grandchallenge.subdomains.utils import reverse
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
)
from tests.factories import StagedFileFactory, UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_create_link_view(client, settings):
    user = UserFactory()

    response = get_view_for_user(
        viewname="algorithms:list", client=client, user=user
    )
    assert reverse("algorithms:create") not in response.rendered_content

    g = Group.objects.get(name=settings.ALGORITHMS_CREATORS_GROUP_NAME)
    g.user_set.add(user)

    response = get_view_for_user(
        viewname="algorithms:list", client=client, user=user
    )
    assert reverse("algorithms:create") in response.rendered_content


@pytest.mark.django_db
def test_algorithm_list_view(client):
    alg1, alg2 = AlgorithmFactory(), AlgorithmFactory()
    user = UserFactory()

    alg1.add_user(user)
    alg2.add_user(user)

    response = get_view_for_user(
        viewname="algorithms:list", client=client, user=user
    )

    assert alg1.get_absolute_url() in response.rendered_content
    assert alg2.get_absolute_url() in response.rendered_content

    alg1.remove_user(user)

    response = get_view_for_user(
        viewname="algorithms:list", client=client, user=user
    )

    assert alg1.get_absolute_url() not in response.rendered_content
    assert alg2.get_absolute_url() in response.rendered_content


@pytest.mark.django_db
def test_algorithm_list_view_filter(client):
    user = UserFactory()
    alg1, alg2, pubalg = (
        AlgorithmFactory(),
        AlgorithmFactory(),
        AlgorithmFactory(visible_to_public=True),
    )
    alg1.add_user(user)

    response = get_view_for_user(
        viewname="algorithms:list", client=client, user=user
    )

    assert response.status_code == 200
    assert alg1.get_absolute_url() in response.rendered_content
    assert alg2.get_absolute_url() not in response.rendered_content
    assert pubalg.get_absolute_url() in response.rendered_content


@pytest.mark.django_db
def test_algorithm_image_create_link_view(client):
    alg = AlgorithmFactory()
    expected_url = reverse(
        "algorithms:image-create", kwargs={"slug": alg.slug}
    )
    user = UserFactory()

    alg.add_user(user)

    response = get_view_for_user(
        viewname="algorithms:detail",
        reverse_kwargs={"slug": alg.slug},
        client=client,
        user=user,
    )
    assert response.status_code == 200
    assert expected_url not in response.rendered_content

    alg.add_editor(user)

    response = get_view_for_user(
        viewname="algorithms:detail",
        reverse_kwargs={"slug": alg.slug},
        client=client,
        user=user,
    )
    assert response.status_code == 200
    assert expected_url in response.rendered_content


@pytest.mark.django_db
def test_algorithm_image_create_detail(client):
    user = UserFactory()
    algorithm = AlgorithmFactory()
    algorithm.add_editor(user)

    algorithm_image = StagedFileFactory(file__filename="test_image.tar.gz")
    response = get_view_for_user(
        client=client,
        viewname="algorithms:image-create",
        reverse_kwargs={"slug": algorithm.slug},
        user=user,
    )
    assert response.status_code == 200

    assert AlgorithmImage.objects.all().count() == 0

    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="algorithms:image-create",
        reverse_kwargs={"slug": algorithm.slug},
        user=user,
        data={"chunked_upload": algorithm_image.file_id},
    )
    assert response.status_code == 302

    images = AlgorithmImage.objects.all()
    assert len(images) == 1
    assert images[0].algorithm == algorithm
    assert response.url == reverse(
        "algorithms:image-detail",
        kwargs={"slug": algorithm.slug, "pk": images[0].pk},
    )


@pytest.mark.django_db
def test_algorithm_run(client):
    user = UserFactory()
    ai1 = AlgorithmImageFactory(ready=True)
    ai1.algorithm.users_group.user_set.add(user)

    response = get_view_for_user(
        viewname="algorithms:execution-session-create",
        reverse_kwargs={"slug": slugify(ai1.algorithm.slug)},
        client=client,
        user=user,
    )

    assert response.status_code == 200
