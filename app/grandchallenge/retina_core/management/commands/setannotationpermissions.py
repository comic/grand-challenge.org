from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from guardian.shortcuts import assign_perm, remove_perm

from grandchallenge.annotations.models import (
    BooleanClassificationAnnotation,
    CoordinateListAnnotation,
    ETDRSGridAnnotation,
    IntegerClassificationAnnotation,
    LandmarkAnnotationSet,
    MeasurementAnnotation,
    PolygonAnnotationSet,
    SingleLandmarkAnnotation,
    SinglePolygonAnnotation,
)

# Existing annotation (name, codename) as of annotations.0001_initial
ANNOTATION_MODELS = (
    MeasurementAnnotation,
    BooleanClassificationAnnotation,
    IntegerClassificationAnnotation,
    PolygonAnnotationSet,
    LandmarkAnnotationSet,
    ETDRSGridAnnotation,
    CoordinateListAnnotation,
    SingleLandmarkAnnotation,
    SinglePolygonAnnotation,
)

WARNING_TEXT = (
    "Only {} model level permissions {}. No annotation objects found."
)
SUCCESS_TEXT = (
    "Done! {} model level permissions and {} object level permissions {}."
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
    for annotation_model in ANNOTATION_MODELS:
        annotation_codename = annotation_model._meta.model_name
        permissions = annotation_model._meta.default_permissions
        # Change user level object permissions to owners of annotations
        for annotation in annotation_model.objects.all():
            if annotation_codename.startswith("single"):
                owner = annotation.annotation_set.grader
            else:
                owner = annotation.grader

            if owner.groups.filter(
                name=settings.RETINA_GRADERS_GROUP_NAME
            ).exists():
                for permission_type in permissions:
                    change_permission_func(
                        f"annotations.{permission_type}_{annotation_codename}",
                        owner,
                        annotation,
                    )
                olp_count += 1

        # Change group level permissions
        for permission_type in permissions:
            change_permission_func(
                f"annotations.{permission_type}_{annotation_codename}",
                retina_admin_group,
            )
        mlp_count += 1

    return mlp_count, olp_count


class Command(BaseCommand):
    """
    Assign or remove all required permissions for annotations to retina_admins.

    Includes table and object level permissions for every annotation owner
    that is in the retina_grader group. This command is probably for one time
    use only so it would be better to implement as data migration,
    however the django-guardian permission model doesn't work nicely with
    data migrations. As explained in
    https://github.com/django-guardian/django-guardian/issues/281
    """

    help = (
        "Assign/remove model level permissions for annotations to "
        "the retina_admins group and object level permissions for "
        "annotations owned by an user in the retina_graders group"
    )

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
        if mlp_count == len(ANNOTATION_MODELS) and olp_count == 0:
            self.stdout.write(
                self.style.WARNING(
                    WARNING_TEXT.format(mlp_count * 4, assigned_text)
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    SUCCESS_TEXT.format(
                        mlp_count * 4, olp_count * 4, assigned_text
                    )
                )
            )
