import pytest
from io import StringIO
from django.core.management import call_command, CommandError
from django.conf import settings
from django.contrib.auth.models import Group

from grandchallenge.retina_core.management.commands.setannotationpermissions import (
    ANNOTATION_CODENAMES,
    PERMISSION_TYPES,
    WARNING_TEXT,
    SUCCESS_TEXT,
)


@pytest.mark.django_db
class TestCommand:
    nr_of_mlps = len(ANNOTATION_CODENAMES) * len(PERMISSION_TYPES)
    nr_of_olps = 21 * len(
        PERMISSION_TYPES
    )  # 21 == nr of annotation models in AnnotationSet fixture

    def test_setannotationpermissions_no_annotations(self):
        out = StringIO()
        call_command("setannotationpermissions", stdout=out)
        output = out.getvalue()
        assert WARNING_TEXT.format(self.nr_of_mlps, "assigned") in output

    def test_setannotationpermissions_no_annotations_remove(self):
        out = StringIO()
        call_command("setannotationpermissions", remove=True, stdout=out)
        output = out.getvalue()
        assert WARNING_TEXT.format(self.nr_of_mlps, "removed") in output

    def test_setannotationpermissions_no_retina_grader_annotations(
        self, AnnotationSet
    ):
        out = StringIO()
        call_command("setannotationpermissions", stdout=out)
        output = out.getvalue()
        assert WARNING_TEXT.format(self.nr_of_mlps, "assigned") in output

    def test_setannotationpermissions(self, AnnotationSet):
        AnnotationSet.grader.groups.add(
            Group.objects.get(name=settings.RETINA_GRADERS_GROUP_NAME)
        )
        out = StringIO()
        call_command("setannotationpermissions", stdout=out)
        output = out.getvalue()
        assert (
            SUCCESS_TEXT.format(self.nr_of_mlps, self.nr_of_olps, "assigned")
            in output
        )

    def test_setannotationpermissions_remove(self, AnnotationSet):
        AnnotationSet.grader.groups.add(
            Group.objects.get(name=settings.RETINA_GRADERS_GROUP_NAME)
        )
        out = StringIO()
        call_command("setannotationpermissions", remove=True, stdout=out)
        output = out.getvalue()
        assert (
            SUCCESS_TEXT.format(self.nr_of_mlps, self.nr_of_olps, "removed")
            in output
        )
