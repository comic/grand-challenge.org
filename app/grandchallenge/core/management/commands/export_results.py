import json

from django.core.management import BaseCommand

from grandchallenge.challenges.models import Challenge
from grandchallenge.evaluation.models import Result


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("challenge_short_name", nargs="+", type=str)

    def handle(self, *args, **options):
        challenge = Challenge.objects.get(
            short_name__iexact=options["challenge_short_name"][0]
        )

        results = Result.objects.filter(
            job__method__challenge=challenge,
        ).select_related("job__submission", "job__method")

        print("[")

        for r in results:
            out = {
                "pk": str(r.pk),
                "created": r.created.isoformat(),
                "job": str(r.job.pk),
                "submission": str(r.job.submission.pk),
                "submission_comment": r.job.submission.comment,
                "submission_file": r.job.submission.file.url
                if r.job.submission.file
                else None,
                "supplementary_file": r.job.submission.supplementary_file.url
                if r.job.submission.supplementary_file
                else None,
                "publication": r.job.submission.publication_url,
                "method": str(r.job.method.pk),
                "creator": str(r.job.submission.creator),
                "published": r.published,
                "metrics": r.metrics,
                "rank": r.rank,
                "rank_score": r.rank_score,
                "rank_per_metric": r.rank_per_metric,
            }
            print(json.dumps(out, indent=2) + ",")

        print("]")
