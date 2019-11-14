from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError
from guardian.shortcuts import assign_perm

from grandchallenge.annotations.models import (
    BooleanClassificationAnnotation,
    CoordinateListAnnotation,
    ETDRSGridAnnotation,
    IntegerClassificationAnnotation,
    LandmarkAnnotationSet,
    MeasurementAnnotation,
    PolygonAnnotationSet,
)


class Command(BaseCommand):
    """
    Copy all annotations that belong to one user to another user.

    Currently, this command is used for debugging purposes to copy the
    (imported) annotations of a certain user to the demo user. This function
    will also be used to copy the imported annotations of the old workstation
    to the new grader accounts.
    """

    help = "Copy annotations from one user to another"

    def add_arguments(self, parser):
        parser.add_argument(
            "user_from",
            type=str,
            help="Username of user where annotations will be copied from",
        )
        parser.add_argument(
            "user_to",
            type=str,
            help="Username of user where annotations will be copied to",
        )

        parser.add_argument(
            "-p",
            "--add_permissions",
            type=bool,
            default=True,
            help="Adds object level permissions to user_to for the each of the annotation instances",
        )

    def handle(self, *args, **options):  # noqa: C901
        try:
            user_from = get_user_model().objects.get(
                username=options["user_from"]
            )
        except ObjectDoesNotExist:
            raise CommandError("user_from does not exist")

        try:
            user_to = get_user_model().objects.get(username=options["user_to"])
        except ObjectDoesNotExist:
            raise CommandError("user_to does not exist")

        total_parents_copied = 0
        total_children_copied = 0
        for model in (
            MeasurementAnnotation,
            BooleanClassificationAnnotation,
            IntegerClassificationAnnotation,
            PolygonAnnotationSet,
            LandmarkAnnotationSet,
            ETDRSGridAnnotation,
            CoordinateListAnnotation,
        ):
            for obj in model.objects.filter(grader=user_from):
                # For annotations with child models, also copy those models
                children = []
                if model == PolygonAnnotationSet:
                    children = obj.singlepolygonannotation_set.all()
                if model == LandmarkAnnotationSet:
                    children = obj.singlelandmarkannotation_set.all()

                # Save annotation copy
                obj_pk = obj.pk
                obj.grader_id = user_to.id
                obj.pk = None
                obj.save()
                if options["add_permissions"]:
                    for permission_type in obj._meta.default_permissions:
                        assign_perm(
                            f"{obj._meta.app_label}.{permission_type}_{obj._meta.model_name}",
                            user_to,
                            obj,
                        )

                # Save child model copies
                for child in children:
                    child.pk = None
                    child.annotation_set = obj
                    child.save()
                    if options["add_permissions"]:
                        for permission_type in child._meta.default_permissions:
                            assign_perm(
                                f"{child._meta.app_label}.{permission_type}_{child._meta.model_name}",
                                user_to,
                                child,
                            )

                with_children_output = (
                    f" with {str(len(children))} children"
                    if len(children)
                    else ""
                )
                self.stdout.write(
                    f"Copied {str(obj._meta.object_name)}({obj_pk}){with_children_output}"
                )

                total_parents_copied += 1
                total_children_copied += len(children)

        if total_parents_copied == 0:
            raise CommandError("No annotations found for this user")
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Done! Copied {total_parents_copied} annotations/sets and {total_children_copied} children"
                )
            )
