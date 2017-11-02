import os

import factory
import pytest
from django.db.models import signals

from evaluation.tasks import evaluate_submission
from evaluation.tests.factories import SubmissionFactory, JobFactory


@pytest.mark.django_db
@factory.django.mute_signals(signals.post_save)
def test_submission_evaluation():
    # Upload a submission and create a job
    testfile = os.path.join(os.path.split(__file__)[0], 'resources',
                            'compressed.zip')

    submission = SubmissionFactory(file__from_path=testfile)

    job = JobFactory(submission=submission)

    res = evaluate_submission(job=job)
    assert res == 'hello world\n'
