import re

from crispy_forms.helper import FormHelper
from crispy_forms.layout import (
    HTML,
    ButtonHolder,
    Field,
    Fieldset,
    Layout,
    Submit,
)
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.forms import (
    ChoiceField,
    Form,
    HiddenInput,
    IntegerField,
    ModelChoiceField,
    ModelForm,
    ModelMultipleChoiceField,
    Select,
    TextInput,
)
from django.forms.widgets import MultipleHiddenInput
from django.utils.html import format_html
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
from grandchallenge.core.templatetags.remove_whitespace import oxford_comma
from grandchallenge.core.widgets import MarkdownEditorWidget
from grandchallenge.groups.forms import UserGroupForm
from grandchallenge.hanging_protocols.forms import ViewContentMixin
from grandchallenge.subdomains.utils import reverse_lazy
from grandchallenge.workstations.models import Workstation


class ModelFactsTextField(Field):
    """Custom field template that renders the help text above the field rather than below it."""

    template = "algorithms/model_facts_field.html"


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


class RepoNameValidationMixin:
    def clean_repo_name(self):
        repo_name = self.cleaned_data.get("repo_name")

        if repo_name != "":
            pattern = re.compile("^([^/]+/[^/]+)$")

            if "github.com" in repo_name:
                raise ValidationError(
                    "Please only provide the repository name, not the full "
                    "url. E.g. 'comic/grand-challenge.org'"
                )

            if not pattern.match(repo_name):
                raise ValidationError(
                    "Please make sure you provide the repository name in the "
                    "format '<owner>/<repo>', e.g. 'comic/grand-challenge.org'"
                )

            if (
                Algorithm.objects.exclude(pk=self.instance.pk)
                .filter(repo_name=repo_name)
                .exists()
            ):
                raise ValidationError(
                    "This repository is already linked to another algorithm"
                )

        return repo_name


class AlgorithmPublishValidation:
    def clean_public(self):
        public = self.cleaned_data.get("public")
        # presence of a contact email is already checked
        if public and (
            not self.instance.summary
            or not self.instance.public_test_case
            or not self.instance.mechanism
            or not self.instance.display_editors
        ):
            raise ValidationError(
                "To publish this algorithm you need at least 1 public test case with a successful result from the latest version of the algorithm. You also need a summary and description of the mechanism of your algorithm. The link to update your algorithm description can be found on the algorithm information page."
            )
        return public


class AlgorithmIOValidationMixin:
    def clean(self):
        cleaned_data = super().clean()

        duplicate_interfaces = {*cleaned_data.get("inputs", [])}.intersection(
            {*cleaned_data.get("outputs", [])}
        )

        if duplicate_interfaces:
            raise ValidationError(
                f"The sets of Inputs and Outputs must be unique: "
                f"{oxford_comma(duplicate_interfaces)} present in both"
            )

        return cleaned_data


class AlgorithmForm(
    RepoNameValidationMixin,
    AlgorithmIOValidationMixin,
    AlgorithmPublishValidation,
    WorkstationUserFilterMixin,
    ModelForm,
    ViewContentMixin,
):
    image_requires_memory_gb = IntegerField(
        min_value=settings.ALGORITHMS_MIN_MEMORY_GB,
        max_value=settings.ALGORITHMS_MAX_MEMORY_GB,
        initial=15,
        help_text="The maximum system memory required by the algorithm in gigabytes.",
    )
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
            reverse_lazy("components:component-interface-list-algorithms"),
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
            reverse_lazy("components:component-interface-list-algorithms"),
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
            "inputs",
            "outputs",
            "workstation",
            "workstation_config",
            "hanging_protocol",
            "view_content",
            "credits_per_job",
            "detail_page_markdown",
            "job_create_page_markdown",
            "additional_terms_markdown",
            "result_template",
            "image_requires_gpu",
            "image_requires_memory_gb",
            "recurse_submodules",
            "contact_email",
            "display_editors",
            "access_request_handling",
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
            "display_editors": Select(
                choices=(("", "-----"), (True, "Yes"), (False, "No"))
            ),
        }
        widgets.update(ViewContentMixin.Meta.widgets)
        help_texts = {
            "repo_name": format_html(
                (
                    "The full name of the repository to use as a source to build "
                    "your algorithm images, in the form {{owner}}/{{repo}}. "
                    "Please note that this is an optional field. Only fill "
                    "out this field in case the "
                    '<a href="{}" target="_blank">Grand Challenge GitHub app</a> '
                    "has been installed for your repository. "
                    "We strongly encourage users to use the 'Link GitHub repo' "
                    "button under the 'Containers' menu item to link a repo "
                    "instead of manually altering this field."
                ),
                settings.GITHUB_APP_INSTALL_URL,
            ),
            "workstation_config": format_lazy(
                (
                    "The viewer configuration to use for this algorithm. "
                    "If a suitable configuration does not exist you can "
                    '<a href="{}">create a new one</a>. For a list of existing '
                    'configurations, go <a href="{}">here</a>.'
                ),
                reverse_lazy("workstation-configs:create"),
                reverse_lazy("workstation-configs:list"),
            ),
            "publications": format_lazy(
                (
                    "The publications associated with this algorithm. "
                    'If your publication is missing click <a href="{}">here</a> to add it '
                    "and then refresh this page."
                ),
                reverse_lazy("publications:create"),
            ),
            "description": "Short description of this algorithm, max 1024 characters. This will appear in the info modal on the algorithm overview list.",
            "detail_page_markdown": "<span class='text-danger'><i class='fa fa-exclamation-triangle'></i> This field will be deprecated. Please use the separate 'Algorithm description' form on the Information page to describe your algorithm instead.</span>",
            "hanging_protocol": format_lazy(
                (
                    "The hanging protocol to use for this algorithm. "
                    "If a suitable protocol does not exist you can "
                    '<a href="{}">create a new one</a>. For a list of existing '
                    'hanging protocols, go <a href="{}">here</a>.'
                ),
                reverse_lazy("hanging-protocols:create"),
                reverse_lazy("hanging-protocols:list"),
            ),
        }
        help_texts.update(ViewContentMixin.Meta.help_texts)
        labels = {
            "workstation": "Viewer",
            "workstation_config": "Viewer Configuration",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Fieldset(
                "",
                "title",
                "description",
                "contact_email",
                "display_editors",
                "public",
                "access_request_handling",
                "organizations",
                "publications",
                "modalities",
                "structures",
                "logo",
                "social_image",
                "workstation",
                "workstation_config",
                "hanging_protocol",
                "view_content",
                "inputs",
                "outputs",
                "credits_per_job",
                "image_requires_gpu",
                "image_requires_memory_gb",
                ModelFactsTextField("detail_page_markdown"),
                "additional_terms_markdown",
                "job_create_page_markdown",
                "result_template",
                "recurse_submodules",
            ),
            ButtonHolder(Submit("save", "Save")),
        )

        self.fields["contact_email"].required = True
        self.fields["display_editors"].required = True
        if self.instance:
            self.fields["view_content"].help_text += (
                " The following interfaces are used in your algorithm: "
                f"{', '.join(self.instance.inputs.values_list('slug', flat=True).distinct())}."
            )


class AlgorithmForPhaseForm(SaveFormInitMixin, ModelForm):
    class Meta:
        model = Algorithm
        fields = (
            "title",
            "description",
            "modalities",
            "structures",
            "inputs",
            "outputs",
            "workstation",
            "workstation_config",
            "hanging_protocol",
            "view_content",
            "image_requires_gpu",
            "image_requires_memory_gb",
            "contact_email",
            "display_editors",
            "logo",
        )
        widgets = {
            "description": TextInput,
            "workstation_config": HiddenInput(),
            "hanging_protocol": HiddenInput(),
            "view_content": HiddenInput(),
            "display_editors": HiddenInput(),
            "contact_email": HiddenInput(),
            "workstation": HiddenInput(),
            "inputs": MultipleHiddenInput(),
            "outputs": MultipleHiddenInput(),
            "modalities": MultipleHiddenInput(),
            "structures": MultipleHiddenInput(),
            "logo": HiddenInput(),
        }
        help_texts = {
            "description": "Short description of this algorithm, max 1024 characters. This will appear in the info modal on the algorithm overview list.",
        }

    def __init__(
        self,
        workstation_config,
        hanging_protocol,
        view_content,
        display_editors,
        contact_email,
        workstation,
        inputs,
        outputs,
        structures,
        modalities,
        logo,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.fields["workstation_config"].initial = workstation_config
        self.fields["workstation_config"].disabled = True
        self.fields["hanging_protocol"].initial = hanging_protocol
        self.fields["hanging_protocol"].disabled = True
        self.fields["view_content"].initial = view_content
        self.fields["view_content"].disabled = True
        self.fields["display_editors"].initial = display_editors
        self.fields["display_editors"].disabled = True
        self.fields["contact_email"].initial = contact_email
        self.fields["contact_email"].disabled = True
        self.fields["workstation"].initial = (
            workstation
            if workstation
            else Workstation.objects.get(
                slug=settings.DEFAULT_WORKSTATION_SLUG
            )
        )
        self.fields["workstation"].disabled = True
        self.fields["inputs"].initial = inputs
        self.fields["inputs"].disabled = True
        self.fields["outputs"].initial = outputs
        self.fields["outputs"].disabled = True
        self.fields["modalities"].initial = modalities
        self.fields["modalities"].disabled = True
        self.fields["structures"].initial = structures
        self.fields["structures"].disabled = True
        self.fields["logo"].initial = logo
        self.fields["logo"].disabled = True


class AlgorithmDescriptionForm(ModelForm):
    class Meta:
        model = Algorithm
        fields = (
            "summary",
            "mechanism",
            "uses_and_directions",
            "validation_and_performance",
            "warnings",
            "common_error_messages",
            "editor_notes",
        )
        widgets = {
            "summary": MarkdownEditorWidget,
            "mechanism": MarkdownEditorWidget,
            "uses_and_directions": MarkdownEditorWidget,
            "validation_and_performance": MarkdownEditorWidget,
            "warnings": MarkdownEditorWidget,
            "common_error_messages": MarkdownEditorWidget,
            "editor_notes": MarkdownEditorWidget,
        }
        help_texts = {
            "validation_and_performance": "If you have performance metrics about your algorithm, you can report them here. We recommend doing this in a table. <br>"
            'Use a <a href = "https://www.tablesgenerator.com/markdown_tables"> markdown table generator</a>, or the following example to create your table:<br><br>'
            "| | Metric 1 | Metric 2 |<br>"
            "| --------- | --------- | -------- |<br>"
            "| group 1 | 60% | 0.58 |<br>"
            "| group 2 | 71% | 0.72 |<br>",
            "mechanism": "Provide a short technical description of your algorithm. Think about the following aspects: <br>"
            "- Target population: What clinical population does your algorithm target? <br>"
            "- Algorithm description: Please provide a brief description of the methods of your algorithm.<br>"
            "- Inputs and Outputs: The inputs and outputs your algorithm accepts and produces are automatically listed on the information page. <br>&nbsp;&nbsp;&nbsp;"
            "Use this space here to provide additional details about them, if you wish.",
            "common_error_messages": "Describe common error messages a user might encounter when trying out your algorithm and provide solutions for them. <br>"
            "You might want to consider listing them in a table like this:<br><br>"
            "| Error message | Solution | <br>"
            "| --------- | ----------- | <br>"
            "| error 1 | solution 1| <br>",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Fieldset(
                "",
                HTML(
                    """
                    <p class="mt-2">To make your algorithm accessible to other users, we ask you to provide some background information on how your algorithm works.
                    Please refer to our <a href="https://grand-challenge.org/documentation/documenting-your-algorithm-for-users/">documentation</a> for examples for each of the sections below.
                    Once filled in, the background information will appear in the 'Information' section on your algorithm page.
                    It will be shown exactly as you style it here in the markdown editor, so make sure to check the preview before saving your changes.</p>
                """
                ),
                ModelFactsTextField("summary"),
                ModelFactsTextField("mechanism"),
                ModelFactsTextField("validation_and_performance"),
                ModelFactsTextField("uses_and_directions"),
                ModelFactsTextField("warnings"),
                ModelFactsTextField("common_error_messages"),
                ModelFactsTextField("editor_notes"),
            ),
            ButtonHolder(Submit("save", "Save")),
        )


class AlgorithmUpdateForm(AlgorithmForm):
    class Meta(AlgorithmForm.Meta):
        fields = AlgorithmForm.Meta.fields + ("repo_name",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.layout[0].append("repo_name")


class AlgorithmImageForm(ContainerImageForm):
    requires_memory_gb = IntegerField(
        min_value=settings.ALGORITHMS_MIN_MEMORY_GB,
        max_value=settings.ALGORITHMS_MAX_MEMORY_GB,
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


class AlgorithmRepoForm(RepoNameValidationMixin, SaveFormInitMixin, ModelForm):
    repo_name = ChoiceField()

    def __init__(self, *args, **kwargs):
        repos = kwargs.pop("repos")
        super().__init__(*args, **kwargs)
        self.fields["repo_name"].choices = [(repo, repo) for repo in repos]

    class Meta:
        model = Algorithm
        fields = ("repo_name",)


class AlgorithmPublishForm(AlgorithmPublishValidation, ModelForm):
    class Meta:
        model = Algorithm
        fields = ("public",)
