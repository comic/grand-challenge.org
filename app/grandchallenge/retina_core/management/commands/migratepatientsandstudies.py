from django.core.management.base import BaseCommand
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models.functions import Length

from grandchallenge.cases.models import Image
from grandchallenge.patients.models import Patient
from grandchallenge.studies.models import Study


def iterate_objects(objects, method_to_perform, page_size=100):
    paginator = Paginator(objects, page_size)
    print(f"Found {paginator.count} objects")
    for idx in paginator.page_range:
        print(f"Page {idx} of {paginator.num_pages}")
        page = paginator.page(idx)
        for obj in page.object_list:
            method_to_perform(obj)

    return paginator.count


def migrate_fields(image):
    image.study_description = image.study.name
    image.patient_id = image.study.patient.name
    if image.study.datetime is not None:
        image.study_date = image.study.datetime.date()
    image.save()


def validate_field_lengths():
    patients = Patient.objects.annotate(name_len=Length("name")).filter(
        name_len__gt=64
    )
    studies = Study.objects.annotate(name_len=Length("name")).filter(
        name_len__gt=64
    )
    if len(patients) > 0 or len(studies) > 0:
        raise ValueError(
            "Some patient or study names are too long.\n"
            f"Patients: {', '.join([str(o.pk) for o in patients])}.\n"
            f"Studies: {', '.join([str(o.pk) for o in studies])}."
        )


def perform_migration():
    print("Validating length of name fields on objects...")
    validate_field_lengths()
    print("Field lengths validated. Starting migration...")
    with transaction.atomic():
        images = Image.objects.select_related("study__patient").filter(
            study__isnull=False
        )
        images_changed = iterate_objects(images, migrate_fields)
    print(f"Done! {images_changed} images changed.")
    return images_changed


class Command(BaseCommand):
    help = """Migrate Patient and Study models to fields on the image model.
    The command will first validate the fields to migrate. If validation passes
    the command will execute."""

    def handle(self, *args, **options):
        perform_migration()
