from django.core.management import BaseCommand
from django.core.paginator import Paginator

from grandchallenge.archives.models import ArchiveItem


class Command(BaseCommand):
    def handle(self, *args, **options):
        items = (
            ArchiveItem.objects.select_related("archive")
            .order_by("created")
            .all()
        )
        paginator = Paginator(items, 100)
        num_pages = paginator.end_index()

        for page_nr in paginator.page_range:
            print(f"Page {page_nr} / {num_pages}...")
            for item in paginator.page(page_nr).object_list:
                item.assign_permissions()

        print("Done")
