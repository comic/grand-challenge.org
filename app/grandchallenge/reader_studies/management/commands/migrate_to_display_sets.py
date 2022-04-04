from django.core.management import BaseCommand

from grandchallenge.reader_studies.models import ReaderStudy
from grandchallenge.reader_studies.utils import (
    check_for_new_answers,
    migrate_reader_study_to_display_sets,
)


class Command(BaseCommand):
    def handle(self, *args, **options):
        not_migrated = []
        reader_studies = ReaderStudy.objects.filter(use_display_sets=False)
        n_studies = len(reader_studies)
        self.stdout.write(f"Found {n_studies} objects to migrate.")
        count = 0
        for rs in reader_studies:
            count += 1
            content_keys = {x for item in rs.hanging_list for x in item}
            if not (content_keys in [{"main"}, {"main", "main-overlay"}]):
                # Multiple viewports require more interfaces, this needs
                # to be handled manually
                not_migrated.append(str(rs.pk))
                self.stdout.write(
                    self.style.WARNING(
                        f"Cannot migrate {rs}. ({count}/{n_studies})"
                    )
                )
                continue
            view_content = {"main": "generic-medical-image"}
            if "main-overlay" in content_keys:
                view_content["main-overlay"] = "generic-overlay"

            migrate_reader_study_to_display_sets(rs, view_content)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully migrated {rs}. ({count}/{n_studies})"
                )
            )

            try:
                check_for_new_answers(rs)
            except ValueError as e:
                self.stdout.write(self.style.ERROR(str(e)))

        pk_str = "\n".join(not_migrated)
        self.stdout.write(
            f"{len(not_migrated)} reader studies could not be migrated:\n\n"
            f"{pk_str}"
        )
