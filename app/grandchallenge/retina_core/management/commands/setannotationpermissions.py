from django.core.management.base import BaseCommand, CommandError
from grandchallenge.annotations.models import (
    MeasurementAnnotation,
    BooleanClassificationAnnotation,
    IntegerClassificationAnnotation,
    PolygonAnnotationSet,
    LandmarkAnnotationSet,
    ETDRSGridAnnotation,
    CoordinateListAnnotation,
    SinglePolygonAnnotation,
    SingleLandmarkAnnotation,
)
from django.contrib.auth.models import Group
from django.conf import settings
from guardian.shortcuts import assign_perm, remove_perm

# Permission types
PERMISSION_TYPES = ("view", "add", "change", "delete")

# Existing annotation (name, codename) as of annotations.0001_initial
ANNOTATION_CODENAMES = (
    (BooleanClassificationAnnotation, "booleanclassificationannotation"),
    (CoordinateListAnnotation, "coordinatelistannotation"),
    (IntegerClassificationAnnotation, "integerclassificationannotation"),
    (LandmarkAnnotationSet, "landmarkannotationset"),
    (MeasurementAnnotation, "measurementannotation"),
    (PolygonAnnotationSet, "polygonannotationset"),
    (SingleLandmarkAnnotation, "singlelandmarkannotation"),
    (SinglePolygonAnnotation, "singlepolygonannotation"),
    (ETDRSGridAnnotation, "etdrsgridannotation"),
)


def change_retina_permissions(remove=False):
    if remove:
        change_permission_func = remove_perm
    else:
        change_permission_func = assign_perm

    olp_count = 0  # Object level permissions assigned/removed
    mlp_count = 0  # Model level permissions assigned/removed
    retina_admin_group = Group.objects.get(
        name=settings.RETINA_ADMINS_GROUP_NAME
    )
    for (annotation_model, annotation_codename) in ANNOTATION_CODENAMES:
        # Change user level object permissions to owners of annotations
        for annotation in annotation_model.objects.all():
            if annotation_codename.startswith("single"):
                owner = annotation.annotation_set.grader
            else:
                owner = annotation.grader

            if owner.groups.filter(
                name=settings.RETINA_GRADERS_GROUP_NAME
            ).exists():
                for permission_type in PERMISSION_TYPES:
                    change_permission_func(
                        f"annotations.{permission_type}_{annotation_codename}",
                        owner,
                        annotation,
                    )
                    olp_count += 1

        # Change group level permissions
        for permission_type in PERMISSION_TYPES:
            change_permission_func(
                f"annotations.{permission_type}_{annotation_codename}",
                retina_admin_group,
            )
            mlp_count += 1

    return mlp_count, olp_count


class Command(BaseCommand):
    """
    This command assigns/removes all model level permissions for annotations to the retina_admins group
    and object level permissions for every annotation owner that is in the retina_grader group.
    This command is probably for one time use only so it would be better to implement as data migration,
    however the django-guardian permission model don't work nicely with data migrations. As explained
    in https://github.com/django-guardian/django-guardian/issues/281
    """

    help = "Assign/remove model level permissions for annotations to retina_admins group and object level " \
           "permissions for annotations owned by an user in retina_graders group"

    def add_arguments(self, parser):
        parser.add_argument(
            "-r",
            "--remove",
            type=bool,
            default=False,
            help="If set to True the command will remove all permissions",
        )

    def handle(self, *args, **options):
        mlp_count, olp_count = change_retina_permissions(options["remove"])
        assigned_text = "removed" if options["remove"] else "assigned"
        self.stdout.write(
            self.style.SUCCESS(
                f"Done! {mlp_count} model level permissions and {olp_count} object level permissions {assigned_text}."
            )
        )
