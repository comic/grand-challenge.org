from django.core.management import BaseCommand
from django.db import transaction
from django.db.models import Count

from grandchallenge.cases.models import Image
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)


class Command(BaseCommand):
    def handle(self, *args, **options):
        for ci in ComponentInterface.objects.all():
            with transaction.atomic():
                img_duplicates = (
                    ComponentInterfaceValue.objects.filter(interface=ci)
                    .prefetch_related("image")
                    .values("image")
                    .annotate(img_count=Count("image"))
                    .values("image")
                    .order_by()
                    .filter(img_count__gt=1)
                )
                self.stdout.write(
                    f"Found {img_duplicates.count()} duplicate "
                    f"ComponentInterfaceValues for "
                    f"ComponentInterface {ci}."
                )
                for img in Image.objects.filter(id__in=img_duplicates):
                    civs = img.componentinterfacevalue_set.filter(interface=ci)
                    first = civs.first()
                    for civ in civs:
                        for item in civ.algorithms_jobs_as_input.all():
                            item.inputs.add(first)
                        for item in civ.algorithms_jobs_as_output.all():
                            item.outputs.add(first)
                        for item in civ.answers.all():
                            item.civs.add(first)
                        for item in civ.archive_items.all():
                            item.values.add(first)
                        for item in civ.readerstudies.all():
                            item.civs.add(first)
                    for civ in civs.all()[1:]:
                        civ.delete()
