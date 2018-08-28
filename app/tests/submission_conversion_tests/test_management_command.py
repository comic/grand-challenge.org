# -*- coding: utf-8 -*-
import pytest
from django.core.management import call_command
from django.db.models.signals import post_save
from factory.django import mute_signals

from grandchallenge.datasets.models import ImageSet, AnnotationSet
from tests.factories import (
    ChallengeFactory,
    ImageSetFactory,
    SubmissionFactory,
)


@pytest.mark.django_db
def test_submission_conversion(capsys, submission_file, settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)
    settings.broker_url = ("memory://",)
    settings.backend = "memory"

    challenge = ChallengeFactory()

    ImageSetFactory(phase=ImageSet.TRAINING, challenge=challenge)
    test_set = ImageSetFactory(phase=ImageSet.TESTING, challenge=challenge)

    with mute_signals(post_save):
        submission = SubmissionFactory(
            file__from_path=submission_file, challenge=challenge
        )

    call_command("convertsubmissions", challenge.short_name)

    _, err = capsys.readouterr()

    assert err == ""

    annotation_set = AnnotationSet.objects.all()[0]

    assert annotation_set.submission == submission
    assert annotation_set.base == test_set
