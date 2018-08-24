# -*- coding: utf-8 -*-
import pytest

from grandchallenge.core.urlresolvers import reverse
from grandchallenge.datasets.models import ImageSet
from tests.cases_tests.test_background_tasks import (
    create_raw_upload_image_session
)
from tests.factories import (
    UserFactory,
    SUPER_SECURE_TEST_PASSWORD,
    ChallengeFactory,
)


@pytest.mark.django_db
def test_imageset_creation(client, settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)
    settings.broker_url = ("memory://",)
    settings.backend = "memory"

    user = UserFactory(is_staff=True)
    client.login(username=user.username, password=SUPER_SECURE_TEST_PASSWORD)

    challenge = ChallengeFactory()

    url = reverse(
        "datasets:imageset-create",
        kwargs={"challenge_short_name": challenge.short_name},
    )

    response = client.get(url)
    assert response.status_code == 200

    response = client.post(url, data={"phase": ImageSet.TRAINING})
    assert response.status_code == 302

    imageset = ImageSet.objects.get(
        challenge=challenge, phase=ImageSet.TRAINING
    )

    assert len(imageset.images.all()) == 0
    assert response.url == reverse(
        "datasets:imageset-add-images",
        kwargs={
            "challenge_short_name": challenge.short_name,
            "pk": imageset.pk,
        },
    )

    images = ["image10x10x10.zraw", "image10x10x10.mhd"]
    session, uploaded_images = create_raw_upload_image_session(
        images, imageset=imageset
    )

    response = client.get(imageset.get_absolute_url())

    assert "image10x10x10.mhd" in response.rendered_content
    assert str(session.pk) in response.rendered_content

    imageset.refresh_from_db()

    assert len(imageset.images.all()) == 1
