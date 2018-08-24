# -*- coding: utf-8 -*-
import pytest

from grandchallenge.core.urlresolvers import reverse
from grandchallenge.datasets.models import ImageSet, AnnotationSet
from tests.cases_tests.test_background_tasks import (
    create_raw_upload_image_session
)
from tests.factories import (
    UserFactory,
    SUPER_SECURE_TEST_PASSWORD,
    ChallengeFactory,
    ImageSetFactory,
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


@pytest.mark.django_db
def test_annotationset_creation(client, settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)
    settings.broker_url = ("memory://",)
    settings.backend = "memory"

    user = UserFactory(is_staff=True)
    client.login(username=user.username, password=SUPER_SECURE_TEST_PASSWORD)

    imageset = ImageSetFactory()

    url = reverse(
        "datasets:annotationset-create",
        kwargs={
            "challenge_short_name": imageset.challenge.short_name,
            "base_pk": imageset.pk,
        },
    )

    response = client.get(url)
    assert response.status_code == 200

    response = client.post(url, data={"kind": AnnotationSet.GROUNDTRUTH})
    assert response.status_code == 302

    annotationset = AnnotationSet.objects.get(
        base=imageset, kind=AnnotationSet.GROUNDTRUTH
    )

    assert len(annotationset.images.all()) == 0
    assert annotationset.creator == user
    assert response.url == reverse(
        "datasets:annotationset-add-images",
        kwargs={
            "challenge_short_name": annotationset.base.challenge.short_name,
            "pk": annotationset.pk,
        },
    )

    images = ["image10x10x10.zraw", "image10x10x10.mhd"]
    session, uploaded_images = create_raw_upload_image_session(
        images, annotationset=annotationset
    )

    response = client.get(annotationset.get_absolute_url())

    assert "image10x10x10.mhd" in response.rendered_content
    assert str(session.pk) in response.rendered_content

    annotationset.refresh_from_db()

    assert len(annotationset.images.all()) == 1


@pytest.mark.django_db
def test_unique_dataset_phase(client):
    challenge = ChallengeFactory()
    ImageSetFactory(phase=ImageSet.TRAINING, challenge=challenge)

    user = UserFactory(is_staff=True)
    client.login(username=user.username, password=SUPER_SECURE_TEST_PASSWORD)

    url = reverse(
        "datasets:imageset-create",
        kwargs={"challenge_short_name": challenge.short_name},
    )

    # Creating a training dataset for this challenge should fail
    response = client.post(url, data={"phase": ImageSet.TRAINING})
    assert response.status_code == 200
    assert "already exists" in response.rendered_content

    # But a test dataset should be ok
    response = client.post(url, data={"phase": ImageSet.TESTING})
    assert response.status_code == 302

    # And a training dataset in another challenge should be fine
    url = reverse(
        "datasets:imageset-create",
        kwargs={"challenge_short_name": ChallengeFactory()},
    )
    response = client.post(url, data={"phase": ImageSet.TRAINING})
    assert response.status_code == 302

    assert len(ImageSet.objects.all()) == 3
