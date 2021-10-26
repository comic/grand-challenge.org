import re

from crispy_forms.helper import FormHelper
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.forms import (
    ChoiceField,
    Form,
    HiddenInput,
    IntegerField,
    ModelChoiceField,
    ModelForm,
    ModelMultipleChoiceField,
    TextInput,
)
from django.utils.text import format_lazy
from django_select2.forms import Select2MultipleWidget

from grandchallenge.algorithms.models import (
    Algorithm,
    AlgorithmImage,
    AlgorithmPermissionRequest,
    Job,
)
from grandchallenge.components.form_fields import InterfaceFormField
from grandchallenge.components.forms import ContainerImageForm
from grandchallenge.components.models import (
    ComponentInterface,
    InterfaceKindChoices,
)
from grandchallenge.core.forms import (
    PermissionRequestUpdateForm,
    SaveFormInitMixin,
    WorkstationUserFilterMixin,
)
from grandchallenge.core.templatetags.bleach import clean
from grandchallenge.core.widgets import MarkdownEditorWidget
from grandchallenge.groups.forms import UserGroupForm
from grandchallenge.subdomains.utils import reverse_lazy


class AlgorithmInputsForm(SaveFormInitMixin, Form):
    def __init__(self, *args, algorithm=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        if algorithm is None:
            return

        self.helper = FormHelper()

        for inp in algorithm.inputs.all():
            self.fields[inp.slug] = InterfaceFormField(
                kind=inp.kind,
                schema=inp.schema,
                initial=inp.default_value,
                user=user,
                required=(inp.kind != InterfaceKindChoices.BOOL),
                help_text=clean(inp.description) if inp.description else "",
            ).field


# Exclude interfaces that are not aimed at algorithms from user selection
NON_ALGORITHM_INTERFACES = [
    "predictions-csv-file",
    "predictions-json-file",
    "predictions-zip-file",
    "metrics-json-file",
]


class AlgorithmForm(WorkstationUserFilterMixin, SaveFormInitMixin, ModelForm):
    inputs = ModelMultipleChoiceField(
        queryset=ComponentInterface.objects.exclude(
            slug__in=[*NON_ALGORITHM_INTERFACES, "results-json-file"]
        ),
        widget=Select2MultipleWidget,
        help_text=format_lazy(
            (
                "The inputs to this algorithm. "
                'See the <a href="{}">list of interfaces</a> for more '
                "information about each interface. "
                "Please contact support if your desired input is missing."
            ),
            reverse_lazy("algorithms:component-interface-list"),
        ),
    )
    outputs = ModelMultipleChoiceField(
        queryset=ComponentInterface.objects.exclude(
            slug__in=NON_ALGORITHM_INTERFACES
        ),
        widget=Select2MultipleWidget,
        help_text=format_lazy(
            (
                "The outputs to this algorithm. "
                'See the <a href="{}">list of interfaces</a> for more '
                "information about each interface. "
                "Please contact support if your desired output is missing."
            ),
            reverse_lazy("algorithms:component-interface-list"),
        ),
    )

    class Meta:
        model = Algorithm
        fields = (
            "title",
            "description",
            "publications",
            "modalities",
            "structures",
            "organizations",
            "logo",
            "social_image",
            "public",
            "use_flexible_inputs",
            "repo_name",
            "inputs",
            "outputs",
            "workstation",
            "workstation_config",
            "credits_per_job",
            "detail_page_markdown",
            "job_create_page_markdown",
            "additional_terms_markdown",
            "result_template",
            "image_requires_gpu",
            "image_requires_memory_gb",
            "recurse_submodules",
        )
        widgets = {
            "description": TextInput,
            "detail_page_markdown": MarkdownEditorWidget,
            "job_create_page_markdown": MarkdownEditorWidget,
            "additional_terms_markdown": MarkdownEditorWidget,
            "result_template": MarkdownEditorWidget,
            "publications": Select2MultipleWidget,
            "modalities": Select2MultipleWidget,
            "structures": Select2MultipleWidget,
            "organizations": Select2MultipleWidget,
        }
        help_texts = {
            "workstation_config": format_lazy(
                (
                    "The workstation configuration to use for this algorithm. "
                    "If a suitable configuration does not exist you can "
                    '<a href="{}">create a new one</a>.'
                ),
                reverse_lazy("workstation-configs:create"),
            ),
            "publications": format_lazy(
                (
                    "The publications associated with this reader study. "
                    'If your publication is missing click <a href="{}">here</a> to add it '
                    "and then refresh this page."
                ),
                reverse_lazy("publications:create"),
            ),
        }

    def clean(self):
        cleaned_data = super().clean()

        inputs = {inpt.slug for inpt in cleaned_data["inputs"]}

        if (
            inputs != {"generic-medical-image"}
            and not cleaned_data["use_flexible_inputs"]
        ):
            raise ValidationError(
                "'Use Flexible Inputs' must also be selected when using the "
                "set of inputs you have selected."
            )

        if cleaned_data["repo_name"]:
            pattern = re.compile("^([^/]+/[^/]+)$")
            if "github.com" in cleaned_data["repo_name"]:
                raise ValidationError(
                    "Please only provide the repository name, not the full url. E.g. 'comic/grand-challenge.org'"
                )
            if not pattern.match(cleaned_data["repo_name"]):
                raise ValidationError(
                    "Please make sure you provide the repository name in the format '<owner>/<repo>', e.g. 'comic/grand-challenge.org'"
                )

        return cleaned_data


class AlgorithmImageForm(ContainerImageForm):
    requires_memory_gb = IntegerField(
        min_value=1,
        max_value=30,
        help_text="The maximum system memory required by the algorithm in gigabytes.",
    )
    algorithm = ModelChoiceField(widget=HiddenInput(), queryset=None)

    def __init__(self, *args, algorithm, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["algorithm"].queryset = Algorithm.objects.filter(
            pk=algorithm.pk
        )
        self.fields["algorithm"].initial = algorithm

        self.fields["requires_gpu"].initial = algorithm.image_requires_gpu
        self.fields[
            "requires_memory_gb"
        ].initial = algorithm.image_requires_memory_gb

    class Meta(ContainerImageForm.Meta):
        model = AlgorithmImage
        fields = (
            "requires_gpu",
            "requires_memory_gb",
            "algorithm",
            *ContainerImageForm.Meta.fields,
        )
        labels = {"requires_gpu": "GPU Supported"}
        help_texts = {
            "requires_gpu": "If true, inference jobs for this container will be assigned a GPU"
        }


class AlgorithmImageUpdateForm(SaveFormInitMixin, ModelForm):
    requires_memory_gb = IntegerField(
        min_value=1,
        max_value=30,
        help_text="The maximum system memory required by the algorithm in gigabytes.",
    )

    class Meta:
        model = AlgorithmImage
        fields = ("requires_gpu", "requires_memory_gb")
        labels = {"requires_gpu": "GPU Supported"}
        help_texts = {
            "requires_gpu": "If true, inference jobs for this container will be assigned a GPU"
        }


class UsersForm(UserGroupForm):
    role = "user"

    def add_or_remove_user(self, *, obj):
        super().add_or_remove_user(obj=obj)

        user = self.cleaned_data["user"]

        try:
            permission_request = AlgorithmPermissionRequest.objects.get(
                user=user, algorithm=obj
            )
        except ObjectDoesNotExist:
            return

        if self.cleaned_data["action"] == self.REMOVE:
            permission_request.status = AlgorithmPermissionRequest.REJECTED
        else:
            permission_request.status = AlgorithmPermissionRequest.ACCEPTED

        permission_request.save()


class ViewersForm(UserGroupForm):
    role = "viewer"


class JobForm(SaveFormInitMixin, ModelForm):
    class Meta:
        model = Job
        fields = ("comment", "public")


class AlgorithmPermissionRequestUpdateForm(PermissionRequestUpdateForm):
    class Meta(PermissionRequestUpdateForm.Meta):
        model = AlgorithmPermissionRequest


class AlgorithmRepoForm(SaveFormInitMixin, ModelForm):
    repo_name = ChoiceField()

    def __init__(self, *args, **kwargs):
        repos = kwargs.pop("repos")
        super().__init__(*args, **kwargs)
        self.fields["repo_name"].choices = [(repo, repo) for repo in repos]

    class Meta:
        model = Algorithm
        fields = ("repo_name",)
