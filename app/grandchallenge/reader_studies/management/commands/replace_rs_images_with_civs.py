from django.core.management import BaseCommand
from django.db import transaction

from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.reader_studies.models import Answer, ReaderStudy


class Command(BaseCommand):
    @transaction.atomic
    def replace_image_with_civ(self, obj, ci):
        for image in obj.images.all():
            civ, _ = ComponentInterfaceValue.objects.get_or_create(
                interface=ci, image=image
            )
            obj.civs.add(civ)
        obj.images.clear()
        obj.save()

    def handle(self, *args, **options):
        ci_image = ComponentInterface.objects.get(slug="generic-medical-image")
        for rs in ReaderStudy.objects.all():
            self.replace_image_with_civ(rs, ci_image)

        for ans in Answer.objects.all():
            self.replace_image_with_civ(ans, ci_image)
