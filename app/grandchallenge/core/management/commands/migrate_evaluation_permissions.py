from django.core.management import BaseCommand
from django.core.paginator import Paginator

from grandchallenge.evaluation.models import (
    AlgorithmEvaluation,
    Evaluation,
    Method,
    Phase,
    Submission,
)


class Command(BaseCommand):
    def handle(self, *args, **options):
        for model in [
            Phase,
            Method,
            Submission,
            AlgorithmEvaluation,
            Evaluation,
        ]:
            objs = model.objects.all().order_by("created")
            paginator = Paginator(objs, 100)

            print(f"Found {paginator.count} {model}")

            for idx in paginator.page_range:
                print(f"Page {idx} of {paginator.num_pages}")

                page = paginator.page(idx)

                for o in page.object_list:
                    o.assign_permissions()
