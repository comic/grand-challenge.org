from django.core.management import BaseCommand
from django.core.paginator import Paginator

from grandchallenge.evaluation.models import Method, Submission


class Command(BaseCommand):
    def handle(self, *args, **options):
        for model in [Method, Submission]:

            objects = (
                model.objects.filter(challenge__isnull=False)
                .order_by("created")
                .prefetch_related("challenge__phase")
            )
            paginator = Paginator(objects, 100)

            print(f"Found {paginator.count} {model._meta.model_name}")

            for idx in paginator.page_range:
                print(f"Page {idx} of {paginator.num_pages}")

                page = paginator.page(idx)

                for obj in page.object_list:
                    obj.phase = obj.challenge.phase_set.get()
                    obj.save()
