from django.core.management.base import BaseCommand, CommandError
from grandchallenge.annotations.models import (
    MeasurementAnnotation,
    BooleanClassificationAnnotation,
    PolygonAnnotationSet,
    LandmarkAnnotationSet,
    ETDRSGridAnnotation,
    CoordinateListAnnotation,
)
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist


class Command(BaseCommand):
    """
    This command copies all annotations that belong to one user to another user.
    Currently, it is used for debugging purposes to copy the (imported) annotations of a certain user to the demo user
    """

    help = "Copy annotations from one user to another"

    def add_arguments(self, parser):
        parser.add_argument("user_from")
        parser.add_argument("user_to")

    def handle(self, *args, **options):
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

                # Save child model copies
                for child in children:
                    child.pk = None
                    child.annotation_set = obj
                    child.save()

                with_children_output = (
                    f" with {str(len(children))} children"
                    if len(children)
                    else ""
                )
                self.stdout.write(
                    f"Copied {str(obj.__class__.__name__)}({obj_pk}){with_children_output}"
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
