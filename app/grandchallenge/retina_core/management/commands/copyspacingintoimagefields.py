from django.core.management.base import BaseCommand
from django.core.paginator import Paginator

from grandchallenge.cases.models import Image


class Command(BaseCommand):
    help = "Copy spacing or size from itk header to voxel_(width|height|depth)_mm Image fields"

    def handle(self, *args, **options):
        images = Image.objects.filter(
            archive__title__in=[
                "AREDS - GA selection",
                "RS1",
                "kappadata",
                "Rotterdam_Study_1",
                "Rotterdam Study 1",
                "Australia",
                "RS3",
                "RS2",
            ]
        ).order_by("created")
        paginator = Paginator(images, 100)
        self.stdout.write(f"Found {paginator.count} images")

        failed_ids = []
        for idx in paginator.page_range:
            self.stdout.write(f"Page {idx} of {paginator.num_pages}")
            page = paginator.page(idx)
            for im in page.object_list:
                try:
                    spacing = im.spacing
                    im.voxel_width_mm = spacing[-1]
                    im.voxel_height_mm = spacing[-2]
                    if len(spacing) > 2:
                        im.voxel_depth_mm = spacing[0]
                    im.save()
                    self.stdout.write(
                        f"Copied spacing {spacing} for {im.name}"
                    )
                except Exception as e:
                    self.stderr.write(
                        f"Error for image {im.name}, error: {str(e)}"
                    )
                    failed_ids.append(im.pk)

        if len(failed_ids) > 0:
            self.stdout.write(
                "Done, but some images failed. IDs of failed images:"
            )
            self.stdout.writelines([str(uuid) for uuid in failed_ids])
        else:
            self.stdout.write(self.style.SUCCESS("Finished successfully!"))
