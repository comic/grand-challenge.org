from django_filters import FilterSet, ModelMultipleChoiceFilter
from django_select2.forms import Select2MultipleWidget
from drf_spectacular.utils import extend_schema_field

from grandchallenge.algorithms.models import Job
from grandchallenge.archives.models import Archive
from grandchallenge.cases.models import Image
from grandchallenge.core.filters import EmptyStringFilter
from grandchallenge.reader_studies.models import ReaderStudy


@extend_schema_field({"type": "array", "items": {"type": "string"}})
class UUIDModelMultipleChoiceFilter(ModelMultipleChoiceFilter):
    pass


class ImageFilterSet(FilterSet):
    archive = UUIDModelMultipleChoiceFilter(
        queryset=Archive.objects.all(),
        widget=Select2MultipleWidget,
        label="Archive",
        help_text="Filter images that belong to an archive",
        field_name="componentinterfacevalue__archive_items__archive__pk",
        to_field_name="pk",
    )
    job_input = UUIDModelMultipleChoiceFilter(
        queryset=Job.objects.all(),
        widget=Select2MultipleWidget,
        label="Job Input",
        help_text="Filter images that are used as input to an algorithm job",
        field_name="componentinterfacevalue__algorithm_jobs_as_input__pk",
        to_field_name="pk",
    )
    job_output = UUIDModelMultipleChoiceFilter(
        queryset=Job.objects.all(),
        widget=Select2MultipleWidget,
        label="Job Output",
        help_text="Filter images that are produced as output from an algorithm job",
        field_name="componentinterfacevalue__algorithm_jobs_as_output__pk",
        to_field_name="pk",
    )
    reader_study = UUIDModelMultipleChoiceFilter(
        queryset=ReaderStudy.objects.all(),
        widget=Select2MultipleWidget,
        label="Reader Study",
        help_text="Filter images that belong to a reader study",
        field_name="componentinterfacevalue__display_sets__reader_study__pk",
        to_field_name="pk",
    )
    patient_id__isempty = EmptyStringFilter(field_name="patient_id")
    study_description__isempty = EmptyStringFilter(
        field_name="study_description"
    )

    class Meta:
        model = Image
        fields = (
            "origin",
            "job_input",
            "job_output",
            "archive",
            "reader_study",
            "name",
            "patient_id",
            "patient_name",
            "patient_birth_date",
            "patient_age",
            "patient_sex",
            "study_date",
            "study_instance_uid",
            "series_instance_uid",
            "study_description",
            "series_description",
        )
