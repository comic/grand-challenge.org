from django_filters import FilterSet, ModelMultipleChoiceFilter
from django_select2.forms import Select2MultipleWidget

from grandchallenge.algorithms.models import Job
from grandchallenge.archives.models import Archive
from grandchallenge.cases.models import Image
from grandchallenge.reader_studies.models import ReaderStudy


class ImageFilterSet(FilterSet):
    archive = ModelMultipleChoiceFilter(
        queryset=Archive.objects.all(),
        widget=Select2MultipleWidget,
        label="Archive",
        help_text="Filter images that belong to an archive",
        field_name="componentinterfacevalue__archive_items__archive__pk",
        to_field_name="pk",
    )
    job_input = ModelMultipleChoiceFilter(
        queryset=Job.objects.all(),
        widget=Select2MultipleWidget,
        label="Job Input",
        help_text="Filter images that are used as input to an algorithm job",
        field_name="componentinterfacevalue__algorithm_jobs_as_input__pk",
        to_field_name="pk",
    )
    job_output = ModelMultipleChoiceFilter(
        queryset=Job.objects.all(),
        widget=Select2MultipleWidget,
        label="Job Output",
        help_text="Filter images that are produced as output from an algorithm job",
        field_name="componentinterfacevalue__algorithm_jobs_as_output__pk",
        to_field_name="pk",
    )
    reader_study = ModelMultipleChoiceFilter(
        queryset=ReaderStudy.objects.all(),
        widget=Select2MultipleWidget,
        label="Reader Study",
        help_text="Filter images that belong to a reader study",
        field_name="readerstudies__pk",
        to_field_name="pk",
    )

    class Meta:
        model = Image
        fields = (
            "study",
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
