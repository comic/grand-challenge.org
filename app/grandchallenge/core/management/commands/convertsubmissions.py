# -*- coding: utf-8 -*-
from django.core.management import BaseCommand

from grandchallenge.datasets.models import ImageSet
from grandchallenge.evaluation.models import Submission
from grandchallenge.submission_conversion.models import (
    SubmissionToAnnotationSetJob
)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("challenge_short_name", nargs="+", type=str)

    def handle(self, *args, **options):
        SubmissionToAnnotationSetJob.objects.create(
            base=ImageSet.objects.all()[0],
            submission=Submission.objects.all()[0],
        )
