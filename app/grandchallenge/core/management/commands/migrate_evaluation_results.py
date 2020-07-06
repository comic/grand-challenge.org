from django.core.management import BaseCommand
from django.core.paginator import Paginator

from grandchallenge.challenges.models import Challenge
from grandchallenge.evaluation.models import Job, Result
from grandchallenge.evaluation.tasks import calculate_ranks


class Command(BaseCommand):
    def handle(self, *args, **options):
        results = (
            Result.objects.all().order_by("created").prefetch_related("job")
        )
        paginator = Paginator(results, 100)

        for idx in paginator.page_range:
            print(f"Page {idx} of {paginator.num_pages}")

            page = paginator.page(idx)

            for result in page.object_list:
                if result.job:
                    job = result.job

                    job.create_result(result=result.metrics)

                    Job.objects.filter(pk=job.pk).update(
                        published=result.published
                    )

                    result.job = None
                    result.save()
                else:
                    print(f"Skipping result {result.pk}")

        for challenge in Challenge.objects.filter(use_evaluation=True):
            calculate_ranks.apply_async(kwargs={"challenge_pk": challenge.pk})
