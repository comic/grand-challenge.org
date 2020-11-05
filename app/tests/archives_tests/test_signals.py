import pytest

from tests.archives_tests.utils import TwoArchives
from tests.factories import ImageFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
@pytest.mark.parametrize("reverse", [True, False])
def test_user_can_download_images(client, reverse):  # noqa: C901
    arch_set = TwoArchives()

    im1, im2, im3, im4 = (
        ImageFactory(),
        ImageFactory(),
        ImageFactory(),
        ImageFactory(),
    )

    images = {im1, im2, im3, im4}

    if reverse:
        for im in [im1, im2, im3, im4]:
            im.archive_set.add(arch_set.arch1, arch_set.arch2)
        for im in [im3, im4]:
            im.archive_set.remove(arch_set.arch1, arch_set.arch2)
        for im in [im1, im2]:
            im.archive_set.remove(arch_set.arch2)
    else:
        # Test that adding images works
        arch_set.arch1.images.add(im1, im2, im3, im4)
        # Test that removing images works
        arch_set.arch1.images.remove(im3, im4)

    tests = (
        (None, 200, set()),
        (arch_set.editor1, 200, {im1.pk, im2.pk}),
        (arch_set.uploader1, 200, {im1.pk, im2.pk}),
        (arch_set.user1, 200, {im1.pk, im2.pk}),
        (arch_set.editor2, 200, set()),
        (arch_set.uploader2, 200, set()),
        (arch_set.user2, 200, set()),
        (arch_set.u, 200, set()),
    )

    for test in tests:
        response = get_view_for_user(
            viewname="api:image-list",
            client=client,
            user=test[0],
            content_type="application/json",
        )
        assert response.status_code == test[1]

        pks = [obj["pk"] for obj in response.json()["results"]]

        for pk in test[2]:
            assert str(pk) in pks

        for pk in images - test[2]:
            assert str(pk) not in pks

    # Test clearing
    if reverse:
        im1.archive_set.clear()
        im2.archive_set.clear()
    else:
        arch_set.arch1.images.clear()

    response = get_view_for_user(
        viewname="api:image-list",
        client=client,
        user=arch_set.user1,
        content_type="application/json",
    )
    assert response.status_code == 200

    if reverse:
        # An image is automatically created for the archive in the factory
        # and not removed here
        assert response.json()["count"] == 1
    else:
        assert response.json()["count"] == 0
