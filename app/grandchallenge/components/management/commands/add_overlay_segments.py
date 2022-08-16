import json

from django.core.management import BaseCommand
from django.db.transaction import on_commit

from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.components.tasks import validate_voxel_values


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("json", type=str)

    def handle(self, *args, **options):
        json_str = options["json"]
        mapping = json.loads(json_str)
        for slug in mapping:
            try:
                interface = ComponentInterface.objects.get(slug=slug)
            except ComponentInterface.DoesNotExist:
                self.stdout.error(
                    f"Could not find interface with slug: {slug}."
                )
            interface.overlay_segments = [
                {
                    "voxel_value": int(voxel_value),
                    "name": mapping[slug][voxel_value],
                    "visible": True,
                }
                for voxel_value in mapping[slug]
            ]
            interface.save()

            for civ in ComponentInterfaceValue.objects.filter(
                interface=interface
            ):
                on_commit(
                    validate_voxel_values.signature(
                        kwargs={
                            "civ_pk": str(civ.pk),
                        }
                    ).apply_async
                )
