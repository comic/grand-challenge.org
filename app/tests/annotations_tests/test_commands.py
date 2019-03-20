import pytest
from io import StringIO
from django.forms.models import model_to_dict
from django.core.management import call_command, CommandError
from guardian.core import ObjectPermissionChecker
from tests.factories import UserFactory
from grandchallenge.annotations.models import (
    MeasurementAnnotation,
    BooleanClassificationAnnotation,
    IntegerClassificationAnnotation,
    PolygonAnnotationSet,
    LandmarkAnnotationSet,
    ETDRSGridAnnotation,
    CoordinateListAnnotation,
)


@pytest.mark.django_db
class TestCommands:
    annotations = (
        (MeasurementAnnotation, "measurement"),
        (BooleanClassificationAnnotation, "boolean"),
        (IntegerClassificationAnnotation, "integer"),
        (PolygonAnnotationSet, "polygon"),
        (LandmarkAnnotationSet, "landmark"),
        (ETDRSGridAnnotation, "etdrs"),
        (CoordinateListAnnotation, "coordinatelist"),
    )

    def test_copyannotations_command_requires_arguments(self):
        try:
            call_command("copyannotations")
            assert False
        except CommandError as e:
            assert (
                str(e)
                == "Error: the following arguments are required: user_from, user_to"
            )

    def test_copyannotations_command_invalid_user_from(self):
        non_user = "non_existing_user"
        try:
            call_command("copyannotations", non_user, non_user)
            assert False
        except CommandError as e:
            assert str(e) == "user_from does not exist"

    def test_copyannotations_command_invalid_user_to(self):
        user = UserFactory()
        non_user = "non_existing_user"
        try:
            call_command("copyannotations", user.username, non_user)
            assert False
        except CommandError as e:
            assert str(e) == "user_to does not exist"

    def test_copyannotations_command_no_annotations(self):
        user_from = UserFactory()
        user_to = UserFactory()
        try:
            call_command(
                "copyannotations", user_from.username, user_to.username
            )
            assert False
        except CommandError as e:
            assert str(e) == "No annotations found for this user"

    def test_copyannotations_command_output(self, AnnotationSet):
        user_from = AnnotationSet.grader
        user_to = UserFactory()

        out = StringIO()
        call_command(
            "copyannotations", user_from.username, user_to.username, stdout=out
        )
        output = out.getvalue()
        assert (
            f"Copied MeasurementAnnotation({AnnotationSet.measurement.pk})"
            in output
        )
        assert (
            f"Copied BooleanClassificationAnnotation({AnnotationSet.boolean.pk})"
            in output
        )
        assert (
            f"Copied IntegerClassificationAnnotation({AnnotationSet.integer.pk})"
            in output
        )
        assert (
            f"Copied PolygonAnnotationSet({AnnotationSet.polygon.pk}) with 10 children"
            in output
        )
        assert (
            f"Copied CoordinateListAnnotation({AnnotationSet.coordinatelist.pk})"
            in output
        )
        assert (
            f"Copied LandmarkAnnotationSet({AnnotationSet.landmark.pk}) with 5 children"
            in output
        )
        assert (
            f"Copied ETDRSGridAnnotation({AnnotationSet.etdrs.pk})" in output
        )
        assert "Done! Copied 7 annotations/sets and 15 children" in output

    def test_copyannotations_command_copies_correctly(self, AnnotationSet):
        user_from = AnnotationSet.grader
        user_to = UserFactory()

        call_command(
            "copyannotations",
            user_from.username,
            user_to.username,
            stdout=None,  # suppress output
        )

        # Fields containing (nested) float values. These are skipped in equality check for now
        # because of rounding errors in python.
        # TODO (low prio) create check for these values
        float_fields = (
            "start_voxel",
            "end_voxel",
            "fovea",
            "optic_disk",
            "value",
            "landmarks",
        )

        for model, name in self.annotations:
            models = {
                "original": model_to_dict(getattr(AnnotationSet, name)),
                "copy": model_to_dict(model.objects.get(grader=user_to)),
            }
            # remove some values from model dicts
            for name in ("original", "copy"):
                models[name]["grader"] = None
                for float_field in float_fields:
                    models[name][float_field] = None

            assert models["original"] == models["copy"]

    def test_copyannotations_command_adds_permissions(self, AnnotationSet):
        user_from = AnnotationSet.grader
        user_to = UserFactory()

        call_command(
            "copyannotations",
            user_from.username,
            user_to.username,
            stdout=None,  # suppress output
        )

        checker = ObjectPermissionChecker(user_to)

        for model, _ in self.annotations:
            model_instance = model.objects.get(grader=user_to)
            children = []
            if model == PolygonAnnotationSet:
                children = model_instance.singlepolygonannotation_set.all()
            if model == LandmarkAnnotationSet:
                children = model_instance.singlelandmarkannotation_set.all()

            perms = checker.get_perms(model_instance)
            for permission_type in model._meta.default_permissions:
                assert f"{permission_type}_{model._meta.model_name}" in perms

            if children:
                checker.prefetch_perms(children)
            for child in children:
                perms = checker.get_perms(child)
                child_model_name = children.first()._meta.model_name
                for permission_type in child._meta.default_permissions:
                    assert f"{permission_type}_{child_model_name}" in perms

    def test_copyannotations_command_doesnt_add_permissions(
        self, AnnotationSet
    ):
        user_from = AnnotationSet.grader
        user_to = UserFactory()

        call_command(
            "copyannotations",
            user_from.username,
            user_to.username,
            add_permissions=False,
            stdout=None,  # suppress output
        )

        checker = ObjectPermissionChecker(user_to)

        for model, _ in self.annotations:
            model_instance = model.objects.get(grader=user_to)
            children = []
            if model == PolygonAnnotationSet:
                children = model_instance.singlepolygonannotation_set.all()
            if model == LandmarkAnnotationSet:
                children = model_instance.singlelandmarkannotation_set.all()

            perms = checker.get_perms(model_instance)
            assert len(perms) == 0

            if children:
                checker.prefetch_perms(children)
            for child in children:
                perms = checker.get_perms(child)
                assert len(perms) == 0
