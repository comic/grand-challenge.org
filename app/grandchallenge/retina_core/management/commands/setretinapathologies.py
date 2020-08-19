from django.core.management.base import BaseCommand
from django.core.paginator import Paginator

from grandchallenge.annotations.models import (
    PolygonAnnotationSet,
    RetinaImagePathologyAnnotation,
)


def array_to_string(a):
    if len(a) == 0:
        return "[]"
    return '[\n\t"' + '",\n\t"'.join(map(lambda v: str(v), a)) + '"\n]'


pathology_options = [
    "rf_present",
    "oda_present",
    "myopia_present",
    "other_present",
    "amd_present",
    "dr_present",
    "cysts_present",
]


def set_retina_pathologies(annotations):
    pathology_set = 0
    old_annotation = 0
    non_matching_pathology = []

    paginator = Paginator(annotations, 100)

    print(f"Found {paginator.count} annotations")

    for idx in paginator.page_range:
        print(f"Page {idx} of {paginator.num_pages}")

        page = paginator.page(idx)

        for annotation in page.object_list:
            name_parts = annotation.name.split("::")
            if len(name_parts) < 3 or name_parts[0] != "retina":
                old_annotation += 1
                continue

            if name_parts[2] not in pathology_options:
                non_matching_pathology.append(
                    {"id": annotation.id, "name": annotation.name}
                )
                continue

            (
                pathology_annotation,
                _,
            ) = RetinaImagePathologyAnnotation.objects.get_or_create(
                grader=annotation.grader,
                image=annotation.image,
                defaults={v: False for v in pathology_options},
            )

            setattr(pathology_annotation, name_parts[2], True)
            pathology_annotation.save()
            pathology_set += 1

    return {
        "pathology_set": pathology_set,
        "old_annotation": old_annotation,
        "non_matching_pathology": non_matching_pathology,
    }


class Command(BaseCommand):
    help = "Sets RetinaImagePathologyAnnotation according to new lesion names"

    def handle(self, *args, **options):
        annotations = PolygonAnnotationSet.objects.all().order_by("created")
        result = set_retina_pathologies(annotations)
        print(
            f"Done! {result['pathology_set']} retina pathologies of {len(annotations)} polygon annotations set, {result['old_annotation']} old annotations (non translatable), {len(result['non_matching_pathology'])} non matching pathologies."
        )

        print(
            "non_matching_pathology = "
            + array_to_string(result["non_matching_pathology"])
        )
