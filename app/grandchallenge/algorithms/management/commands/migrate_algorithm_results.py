from django.core.management import BaseCommand
from django.core.paginator import Paginator

from grandchallenge.algorithms.models import (
    DEFAULT_INPUT_INTERFACE_SLUG,
    DEFAULT_OUTPUT_INTERFACE_SLUG,
    Result,
)
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)


class Command(BaseCommand):
    def handle(self, *args, **options):
        results = (
            Result.objects.all().order_by("created").prefetch_related("job")
        )
        paginator = Paginator(results, 100)

        for idx in paginator.page_range:
            print(f"Page {idx} of {paginator.num_pages}")

            page = paginator.page(idx)

            default_input_interface = ComponentInterface.objects.get(
                slug=DEFAULT_INPUT_INTERFACE_SLUG
            )
            default_output_interface = ComponentInterface.objects.get(
                slug=DEFAULT_OUTPUT_INTERFACE_SLUG
            )

            for result in page.object_list:
                job = result.job

                if job.image:
                    job.inputs.set(
                        [
                            ComponentInterfaceValue.objects.create(
                                interface=default_input_interface,
                                image=job.image,
                            )
                        ]
                    )
                    job.outputs.set(
                        [
                            ComponentInterfaceValue.objects.create(
                                interface=default_output_interface, image=im
                            )
                            for im in result.images.all()
                        ]
                    )
                    job.create_result(result=result.output)
                    job.image = None
                    job.comment = result.comment
                    job.public = result.public
                    job.save()
                else:
                    print(f"Skipping job {job.pk} as there is no input image.")
