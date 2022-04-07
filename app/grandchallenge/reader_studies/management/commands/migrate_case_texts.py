from django.core.management import BaseCommand
from django.db import transaction
from django.db.models import Q

from grandchallenge.reader_studies.models import DisplaySet, ReaderStudy


class Command(BaseCommand):
    def handle(self, *args, **options):
        to_migrate = ReaderStudy.objects.exclude(
            Q(case_text={}) | Q(use_display_sets=False)
        ).prefetch_related(
            "display_sets",
            "display_sets__values",
            "display_sets__values__image",
        )
        count = len(to_migrate)
        self.stdout.write(f"Found {count} objects to migrate.")
        for idx, reader_study in enumerate(to_migrate, start=1):
            with transaction.atomic():
                new_case_text = {}
                for key in reader_study.case_text:
                    for ds in DisplaySet.objects.filter(
                        values__image__name=key
                    ):
                        new_case_text[str(ds.pk)] = reader_study.case_text[key]
                else:
                    # Keys that are not a display set pk are ignored, so leave
                    # the key intact
                    self.stdout.write(
                        self.style.WARNING(
                            f"Could not find a display set for key {key}, "
                            "retaining original key."
                        )
                    )
                    new_case_text[key] = reader_study.case_text[key]
                reader_study.case_text = new_case_text
                reader_study.save()
                self.stdout.write(
                    f"Migrated reader study {reader_study.slug} ({idx}/{count})."
                )
