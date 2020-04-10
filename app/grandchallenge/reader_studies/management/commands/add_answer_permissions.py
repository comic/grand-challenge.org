from django.core.management import BaseCommand
from django.core.paginator import Paginator
from guardian.shortcuts import assign_perm

from grandchallenge.reader_studies.models import Answer


class Command(BaseCommand):
    def handle(self, *args, **options):
        answers = Answer.objects.all().select_related("creator")
        paginator = Paginator(answers, 100)

        print(f"Found {paginator.count} answers")

        for idx in paginator.page_range:
            print(f"Page {idx} of {paginator.num_pages}")

            page = paginator.page(idx)

            for answer in page.object_list:
                assign_perm(
                    f"change_{answer._meta.model_name}", answer.creator, answer
                )
