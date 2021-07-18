import json

from django.core.management import BaseCommand

from grandchallenge.challenges.models import Challenge
from grandchallenge.evaluation.models import Evaluation


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("challenge_short_name", nargs="+", type=str)

    def handle(self, *args, **options):
        challenge = Challenge.objects.get(
            short_name__iexact=options["challenge_short_name"][0]
        )

        jobs = (
            Evaluation.objects.filter(method__challenge=challenge,)
            .select_related("submission", "method")
            .prefetch_related("outputs")
        )

        print("[")

        for j in jobs:
            out = {
                "pk": str(j.pk),
                "created": j.created.isoformat(),
                "submission": str(j.submission.pk),
                "submission_comment": j.submission.comment,
                "submission_file": j.submission.predictions_file.url
                if j.submission.predictions_file
                else None,
                "supplementary_file": j.submission.supplementary_file.url
                if j.submission.supplementary_file
                else None,
                "supplementary_url": j.submission.supplementary_url,
                "method": str(j.method.pk),
                "creator": str(j.submission.creator),
                "published": j.published,
                "metrics": j.outputs.get(
                    interface__slug="metrics-json-file"
                ).value,
                "rank": j.rank,
                "rank_score": j.rank_score,
                "rank_per_metric": j.rank_per_metric,
            }
            print(json.dumps(out, indent=2) + ",")

        print("]")
