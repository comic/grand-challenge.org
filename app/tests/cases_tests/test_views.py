# -*- coding: utf-8 -*-
import json

import pytest

from grandchallenge.cases.models import Image, Annotation
from grandchallenge.core.urlresolvers import reverse
from tests.cases_tests.test_background_tasks import (
    create_raw_upload_image_session
)
from tests.factories import UserFactory, SUPER_SECURE_TEST_PASSWORD


@pytest.mark.django_db
def test_annotation_list_filter(client, settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)
    settings.broker_url = ("memory://",)
    settings.backend = "memory"

    images = ["image10x10x10.zraw", "image10x10x10.mhd"]
    session, uploaded_images = create_raw_upload_image_session(images)

    session.refresh_from_db()

    image = Image.objects.get(origin=session)

    user = UserFactory(is_staff=True)
    client.login(username=user.username, password=SUPER_SECURE_TEST_PASSWORD)

    url = reverse("cases:annotation-list", kwargs={"base_pk": image.pk})
    response = client.get(url)

    assert response.status_code == 200

    url = reverse("cases:annotation-create", kwargs={"base_pk": image.pk})
    response = client.get(url)
    assert response.status_code == 200

    assert len(Annotation.objects.all()) == 0
    response = client.post(url, data={"metadata": json.dumps({"foo": "bar"})})
    assert response.status_code == 302

    response = client.get(response.url)
    assert response.status_code == 200

    assert len(Annotation.objects.all()) == 1
    assert Annotation.objects.all()[0].base.pk == image.pk
