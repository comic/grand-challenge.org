from django.core.management import BaseCommand
from django.db.transaction import on_commit

from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.components.tasks import civ_value_to_file


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("interface_slug", type=str)

    def handle(self, *args, **options):
        slug = options["interface_slug"]

        interface = ComponentInterface.objects.get(
            slug=slug, store_in_database=True
        )

        pks = ComponentInterfaceValue.objects.filter(
            interface=interface,
            value__isnull=False,
        ).values_list("pk", flat=True)

        self.stdout.write(f"Convert {len(pks)} values?")
        go = input("To continue enter 'yes': ")

        if go == "yes":
            interface.store_in_database = False
            interface.save()

            for pk in pks:
                on_commit(
                    civ_value_to_file.signature(
                        kwargs={"civ_pk": pk}
                    ).apply_async
                )

        self.stdout.write("Conversion tasks scheduled")
