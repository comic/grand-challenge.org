from pathlib import Path

import pytest
from django.core.management import call_command
from django.db.models.signals import post_save
from factory.django import mute_signals

from grandchallenge.datasets.models import AnnotationSet, ImageSet
from grandchallenge.submission_conversion.models import (
    SubmissionToAnnotationSetJob,
)
from tests.evaluation_tests.factories import SubmissionFactory
from tests.factories import ChallengeFactory


@pytest.mark.django_db
def test_submission_conversion(capsys, submission_file, settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    challenge = ChallengeFactory()

    test_set = challenge.imageset_set.get(phase=ImageSet.TESTING)

    with mute_signals(post_save):
        submission = SubmissionFactory(
            predictions_file__from_path=submission_file,
            phase=challenge.phase_set.get(),
        )

    call_command("convertsubmissions", challenge.short_name)

    _, err = capsys.readouterr()

    assert err == ""
    job = SubmissionToAnnotationSetJob.objects.first()
    assert job.output == ""

    annotation_set = AnnotationSet.objects.all()[0]

    assert annotation_set.submission == submission
    assert annotation_set.base == test_set

    images = annotation_set.images.all()

    assert len(images) == 1
    assert images[0].name == "image10x10x10.mhd"

    with mute_signals(post_save):
        submission = SubmissionFactory(
            predictions_file__from_path=Path(__file__).parent.parent
            / "evaluation_tests"
            / "resources"
            / "submission.csv",
            phase=challenge.phase_set.get(),
        )

    call_command("convertsubmissions", challenge.short_name)

    _, err = capsys.readouterr()

    assert err == ""

    annotation_set = AnnotationSet.objects.all()[1]

    assert annotation_set.submission == submission
    assert annotation_set.base == test_set

    labels = annotation_set.labels

    assert len(labels) == 10
    assert labels[0]["class"] == 0
