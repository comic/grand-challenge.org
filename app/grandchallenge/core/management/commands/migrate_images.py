from pathlib import Path

from django.core.management import BaseCommand
from django.core.paginator import Paginator

from grandchallenge.cases.models import Image, ImageFile, image_file_path


class Command(BaseCommand):
    def handle(self, *args, **options):
        images = (
            Image.objects.all().order_by("created").prefetch_related("files")
        )
        paginator = Paginator(images, 100)

        print(f"Found {paginator.count} images")

        for idx in paginator.page_range:
            print(f"Page {idx} of {paginator.num_pages}")

            page = paginator.page(idx)

            for im in page.object_list:
                for f in im.files.exclude(image_type=ImageFile.IMAGE_TYPE_DZI):
                    old_name = f.file.name
                    new_name = image_file_path(f, Path(f.file.name).name)

                    if old_name == new_name:
                        print(f"Skipping {old_name}")
                    else:
                        print(f"Migrating {old_name} to {new_name}")

                        storage = f.file.storage

                        storage.copy(from_name=old_name, to_name=new_name)

                        f.file.name = new_name
                        f.save()

                        storage.delete(old_name)
