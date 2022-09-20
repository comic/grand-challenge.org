import json

from django.core.management import BaseCommand, CommandError
from django.db.transaction import on_commit

from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.components.tasks import validate_voxel_values
from grandchallenge.core.validators import JSONValidator
from grandchallenge.workstation_configs.models import OVERLAY_SEGMENTS_SCHEMA


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("slug", type=str)
        parser.add_argument("json", type=str)

    def handle(self, *args, **options):
        slug = options["slug"]
        json_str = options["json"]
        mapping = json.loads(json_str)
        try:
            interface = ComponentInterface.objects.get(slug=slug)
        except ComponentInterface.DoesNotExist:
            raise CommandError(f"Could not find interface with slug: {slug}.")
        interface.overlay_segments = [
            {
                "voxel_value": int(voxel_value),
                "name": mapping[voxel_value],
                "visible": True,
            }
            for voxel_value in mapping
        ]
        # Only validate the segments json, as the ci's clean method also
        # checks whether civs already exist
        JSONValidator(schema=OVERLAY_SEGMENTS_SCHEMA)(
            value=interface.overlay_segments
        )
        interface.save()

        for civ in ComponentInterfaceValue.objects.filter(interface=interface):
            on_commit(
                validate_voxel_values.signature(
                    kwargs={
                        "civ_pk": str(civ.pk),
                    }
                ).apply_async
            )
