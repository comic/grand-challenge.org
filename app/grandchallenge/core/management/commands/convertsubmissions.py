from django.core.management import BaseCommand

from grandchallenge.challenges.models import Challenge
from grandchallenge.datasets.models import ImageSet
from grandchallenge.evaluation.models import Submission
from grandchallenge.submission_conversion.models import (
    SubmissionToAnnotationSetJob,
)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("challenge_short_name", nargs="+", type=str)

    def handle(self, *args, **options):
        challenge = Challenge.objects.get(
            short_name__iexact=options["challenge_short_name"][0]
        )

        base = ImageSet.objects.get(
            challenge=challenge, phase=ImageSet.TESTING
        )

        submissions = Submission.objects.filter(
            challenge=challenge, annotationset=None
        )

        for submission in submissions:
            j = SubmissionToAnnotationSetJob.objects.create(
                base=base, submission=submission
            )
            print(f"Created job {j}")
