import re
from itertools import chain
from urllib.parse import urlparse

import requests
from crispy_forms.helper import FormHelper
from crispy_forms.layout import (
    HTML,
    ButtonHolder,
    Field,
    Fieldset,
    Layout,
    Submit,
)
from dal import autocomplete
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.postgres.aggregates import ArrayAgg
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.files.base import ContentFile
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
    RegexValidator,
)
from django.db.models import Count, Exists, Max, OuterRef, Q
from django.db.transaction import on_commit
from django.forms import (
    BooleanField,
    CharField,
    Form,
    HiddenInput,
    ModelChoiceField,
    ModelForm,
    ModelMultipleChoiceField,
    Select,
    TextInput,
    URLField,
)
from django.forms.widgets import (
    MultipleHiddenInput,
    PasswordInput,
    RadioSelect,
)
from django.urls import Resolver404, resolve
from django.utils.functional import cached_property
from django.utils.html import format_html
from django.utils.text import format_lazy
from django_select2.forms import Select2MultipleWidget

from grandchallenge.algorithms.models import (
    Algorithm,
    AlgorithmAlgorithmInterface,
    AlgorithmImage,
    AlgorithmInterface,
    AlgorithmModel,
    AlgorithmPermissionRequest,
    Job,
)
from grandchallenge.algorithms.serializers import (
    AlgorithmImageSerializer,
    AlgorithmSerializer,
)
from grandchallenge.algorithms.tasks import import_remote_algorithm_image
from grandchallenge.components.form_fields import (
    INTERFACE_FORM_FIELD_PREFIX,
    InterfaceFormField,
)
from grandchallenge.components.forms import ContainerImageForm
from grandchallenge.components.models import (
    CIVData,
    ComponentInterface,
    ComponentJob,
    ImportStatusChoices,
    InterfaceKindChoices,
)
from grandchallenge.components.schemas import (
    GPUTypeChoices,
    get_default_gpu_type_choices,
)
from grandchallenge.components.serializers import ComponentInterfaceSerializer
from grandchallenge.components.tasks import assign_tarball_from_upload
from grandchallenge.core.forms import (
    PermissionRequestUpdateForm,
    SaveFormInitMixin,
    WorkstationUserFilterMixin,
)
from grandchallenge.core.guardian import get_objects_for_user
from grandchallenge.core.templatetags.bleach import clean
from grandchallenge.core.templatetags.remove_whitespace import oxford_comma
from grandchallenge.core.widgets import (
    JSONEditorWidget,
    MarkdownEditorInlineWidget,
)
from grandchallenge.evaluation.utils import SubmissionKindChoices, get
from grandchallenge.groups.forms import UserGroupForm
from grandchallenge.hanging_protocols.forms import ViewContentExampleMixin
from grandchallenge.hanging_protocols.models import VIEW_CONTENT_SCHEMA
from grandchallenge.organizations.models import Organization
from grandchallenge.reader_studies.models import ReaderStudy
from grandchallenge.subdomains.utils import reverse, reverse_lazy
from grandchallenge.uploads.models import UserUpload
from grandchallenge.uploads.widgets import UserUploadSingleWidget
from grandchallenge.workstations.models import Workstation


class ModelFactsTextField(Field):
    """Custom field template that renders the help text above the field rather than below it."""

    template = "algorithms/model_facts_field.html"


class JobCreateForm(SaveFormInitMixin, Form):
    algorithm_image = ModelChoiceField(
        queryset=None, disabled=True, required=True, widget=HiddenInput
    )
    algorithm_model = ModelChoiceField(
        queryset=None, disabled=True, required=False, widget=HiddenInput
    )
    creator = ModelChoiceField(
        queryset=None, disabled=True, required=False, widget=HiddenInput
    )
    algorithm_interface = ModelChoiceField(
        queryset=None,
        disabled=True,
        required=True,
        widget=HiddenInput,
    )

    def __init__(self, *args, algorithm, user, interface, **kwargs):
        super().__init__(*args, **kwargs)

        self._algorithm = algorithm

        self.helper = FormHelper()

        self._user = user
        self.fields["creator"].queryset = get_user_model().objects.filter(
            pk=self._user.pk
        )
        self.fields["creator"].initial = self._user

        self.fields["algorithm_interface"].queryset = (
            self._algorithm.interfaces.all()
        )
        self.fields["algorithm_interface"].initial = interface

        self._algorithm_image = self._algorithm.active_image

        active_model = self._algorithm.active_model

        if self._algorithm_image:
            self.fields["algorithm_image"].queryset = (
                AlgorithmImage.objects.filter(pk=self._algorithm_image.pk)
            )
            self.fields["algorithm_image"].initial = self._algorithm_image

        if active_model:
            self.fields["algorithm_model"].queryset = (
                AlgorithmModel.objects.filter(pk=active_model.pk)
            )
            self.fields["algorithm_model"].initial = active_model

        for inp in interface.inputs.all():
            prefixed_interface_slug = (
                f"{INTERFACE_FORM_FIELD_PREFIX}{inp.slug}"
            )

            if prefixed_interface_slug in self.data:
                if inp.kind == ComponentInterface.Kind.ANY:
                    # interfaces for which the data can be a list need
                    # to be retrieved with getlist() from the QueryDict
                    initial = self.data.getlist(prefixed_interface_slug)
                else:
                    initial = self.data[prefixed_interface_slug]
            else:
                initial = None

            self.fields[prefixed_interface_slug] = InterfaceFormField(
                instance=inp,
                initial=initial if initial else inp.default_value,
                user=self._user,
                required=True,
                help_text=clean(inp.description) if inp.description else "",
                form_data=self.data,
            ).field

    @cached_property
    def jobs_limit(self):
        if self._algorithm_image:
            return self._algorithm_image.get_remaining_jobs(user=self._user)
        else:
            return 0

    def clean(self):
        cleaned_data = super().clean()

        if not cleaned_data.get("algorithm_image"):
            raise ValidationError("This algorithm is not ready to be used")

        if self.jobs_limit < 1:
            raise ValidationError("You have run out of algorithm credits")

        cleaned_data = self.reformat_inputs(cleaned_data=cleaned_data)

        if Job.objects.get_jobs_with_same_inputs(
            inputs=cleaned_data["inputs"],
            algorithm_image=cleaned_data["algorithm_image"],
            algorithm_model=cleaned_data["algorithm_model"],
        ):
            raise ValidationError(
                "A result for these inputs with the current image "
                "and model already exists."
            )

        return cleaned_data

    def reformat_inputs(self, *, cleaned_data):
        keys_to_remove = []
        inputs = []
        for k, v in cleaned_data.items():
            if k.startswith(INTERFACE_FORM_FIELD_PREFIX):
                keys_to_remove.append(k)
                inputs.append(
                    CIVData(
                        interface_slug=k[len(INTERFACE_FORM_FIELD_PREFIX) :],
                        value=v,
                    )
                )

        for key in keys_to_remove:
            cleaned_data.pop(key)

        cleaned_data["inputs"] = inputs

        return cleaned_data


# Exclude interfaces that are not aimed at algorithms from user selection
NON_ALGORITHM_INTERFACES = [
    "predictions-csv-file",
    "predictions-json-file",
    "predictions-zip-file",
    "metrics-json-file",
]


class AlgorithmForm(
    WorkstationUserFilterMixin,
    SaveFormInitMixin,
    ViewContentExampleMixin,
    ModelForm,
):
    class Meta:
        model = Algorithm
        fields = (
            "title",
            "description",
            "contact_email",
            "display_editors",
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
            "optional_hanging_protocols",
            "view_content",
            "minimum_credits_per_job",
            "job_requires_gpu_type",
            "job_requires_memory_gb",
            "additional_terms_markdown",
            "job_create_page_markdown",
            "result_template",
        )
        widgets = {
            "description": TextInput,
            "job_create_page_markdown": MarkdownEditorInlineWidget,
            "additional_terms_markdown": MarkdownEditorInlineWidget,
            "result_template": MarkdownEditorInlineWidget,
            "publications": Select2MultipleWidget,
            "modalities": Select2MultipleWidget,
            "structures": Select2MultipleWidget,
            "optional_hanging_protocols": Select2MultipleWidget,
            "organizations": Select2MultipleWidget,
            "display_editors": Select(
                choices=(("", "-----"), (True, "Yes"), (False, "No"))
            ),
            "view_content": JSONEditorWidget(schema=VIEW_CONTENT_SCHEMA),
        }
        help_texts = {
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
            "hanging_protocol": format_lazy(
                (
                    "The default hanging protocol to use for this algorithm. "
                    "If a suitable protocol does not exist you can "
                    '<a href="{}">create a new one</a>. For a list of existing '
                    'hanging protocols, go <a href="{}">here</a>.'
                ),
                reverse_lazy("hanging-protocols:create"),
                reverse_lazy("hanging-protocols:list"),
            ),
            "optional_hanging_protocols": format_lazy(
                (
                    "Other optional hanging protocols that can be used for this algorithm. "
                    "If a suitable protocol does not exist you can "
                    '<a href="{}">create a new one</a>. For a list of existing '
                    'hanging protocols, go <a href="{}">here</a>.'
                ),
                reverse_lazy("hanging-protocols:create"),
                reverse_lazy("hanging-protocols:list"),
            ),
        }
        labels = {
            "workstation": "Viewer",
            "workstation_config": "Viewer Configuration",
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, user=user, **kwargs)
        self._user = user

        self.fields["contact_email"].required = True
        self.fields["display_editors"].required = True

        self.fields["job_requires_gpu_type"].choices = (
            self.selectable_gpu_type_choices
        )
        self.fields["job_requires_memory_gb"].validators = [
            MinValueValidator(settings.ALGORITHMS_MIN_MEMORY_GB),
            MaxValueValidator(self.maximum_settable_memory_gb),
        ]

    @cached_property
    def job_requirement_properties_from_phases(self):
        qs = get_objects_for_user(
            self._user, "evaluation.create_phase_submission"
        )
        inputs = self.instance.inputs.all()
        outputs = self.instance.outputs.all()
        return (
            qs.annotate(
                total_algorithm_input_count=Count(
                    "algorithm_inputs", distinct=True
                ),
                total_algorithm_output_count=Count(
                    "algorithm_outputs", distinct=True
                ),
                relevant_algorithm_input_count=Count(
                    "algorithm_inputs",
                    filter=Q(algorithm_inputs__in=inputs),
                    distinct=True,
                ),
                relevant_algorithm_output_count=Count(
                    "algorithm_outputs",
                    filter=Q(algorithm_outputs__in=outputs),
                    distinct=True,
                ),
            )
            .filter(
                submission_kind=SubmissionKindChoices.ALGORITHM,
                total_algorithm_input_count=len(inputs),
                total_algorithm_output_count=len(outputs),
                relevant_algorithm_input_count=len(inputs),
                relevant_algorithm_output_count=len(outputs),
            )
            .aggregate(
                max_memory=Max("algorithm_maximum_settable_memory_gb"),
                gpu_type_choices=ArrayAgg(
                    "algorithm_selectable_gpu_type_choices", distinct=True
                ),
            )
        )

    @cached_property
    def job_requirement_properties_from_organizations(self):
        return Organization.objects.filter(
            members_group__user=self._user
        ).aggregate(
            max_memory=Max("algorithm_maximum_settable_memory_gb"),
            gpu_type_choices=ArrayAgg(
                "algorithm_selectable_gpu_type_choices", distinct=True
            ),
        )

    @property
    def selectable_gpu_type_choices(self):
        choices_set = {
            self.instance.job_requires_gpu_type,
            *get_default_gpu_type_choices(),
            *chain.from_iterable(
                self.job_requirement_properties_from_phases["gpu_type_choices"]
            ),
            *chain.from_iterable(
                self.job_requirement_properties_from_organizations[
                    "gpu_type_choices"
                ]
            ),
        }
        return [
            (choice.value, choice.label)
            for choice in GPUTypeChoices
            if choice in choices_set
        ]

    @property
    def maximum_settable_memory_gb(self):
        value = settings.ALGORITHMS_MAX_MEMORY_GB
        maximum_in_phases = self.job_requirement_properties_from_phases[
            "max_memory"
        ]
        if maximum_in_phases is not None:
            value = max(value, maximum_in_phases)
        maximum_in_organizations = (
            self.job_requirement_properties_from_organizations["max_memory"]
        )
        if maximum_in_organizations is not None:
            value = max(value, maximum_in_organizations)
        return value


class UserAlgorithmsForPhaseMixin:
    def __init__(self, *args, user, phase, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = user
        self._phase = phase

    def get_phase_algorithm_inputs_outputs(self):
        return (
            self._phase.algorithm_inputs.all(),
            self._phase.algorithm_outputs.all(),
        )

    @cached_property
    def user_algorithms_for_phase(self):
        inputs, outputs = self.get_phase_algorithm_inputs_outputs()
        desired_image_subquery = AlgorithmImage.objects.filter(
            algorithm=OuterRef("pk"), is_desired_version=True
        )
        desired_model_subquery = AlgorithmModel.objects.filter(
            algorithm=OuterRef("pk"), is_desired_version=True
        )
        return (
            get_objects_for_user(self._user, "algorithms.change_algorithm")
            .annotate(
                total_input_count=Count("inputs", distinct=True),
                total_output_count=Count("outputs", distinct=True),
                relevant_input_count=Count(
                    "inputs", filter=Q(inputs__in=inputs), distinct=True
                ),
                relevant_output_count=Count(
                    "outputs", filter=Q(outputs__in=outputs), distinct=True
                ),
                has_active_image=Exists(desired_image_subquery),
                active_image_pk=desired_image_subquery.values_list(
                    "pk", flat=True
                ),
                active_model_pk=desired_model_subquery.values_list(
                    "pk", flat=True
                ),
                active_image_comment=desired_image_subquery.values_list(
                    "comment", flat=True
                ),
                active_model_comment=desired_model_subquery.values_list(
                    "comment", flat=True
                ),
            )
            .filter(
                total_input_count=len(inputs),
                total_output_count=len(outputs),
                relevant_input_count=len(inputs),
                relevant_output_count=len(outputs),
            )
        )

    @cached_property
    def user_algorithm_count(self):
        return self.user_algorithms_for_phase.count()


class AlgorithmForPhaseForm(
    UserAlgorithmsForPhaseMixin, SaveFormInitMixin, ModelForm
):
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
            "optional_hanging_protocols",
            "view_content",
            "job_requires_gpu_type",
            "job_requires_memory_gb",
            "contact_email",
            "display_editors",
            "logo",
            "time_limit",
        )
        widgets = {
            "description": TextInput,
            "workstation_config": HiddenInput(),
            "hanging_protocol": HiddenInput(),
            "optional_hanging_protocols": MultipleHiddenInput(),
            "view_content": HiddenInput(),
            "display_editors": HiddenInput(),
            "contact_email": HiddenInput(),
            "workstation": HiddenInput(),
            "inputs": MultipleHiddenInput(),
            "outputs": MultipleHiddenInput(),
            "modalities": MultipleHiddenInput(),
            "structures": MultipleHiddenInput(),
            "logo": HiddenInput(),
            "time_limit": HiddenInput(),
        }
        help_texts = {
            "description": (
                "Short description of this algorithm, max 1024 characters. "
                "This will appear in the info modal on the algorithm overview list."
            ),
        }

    def __init__(
        self,
        *args,
        workstation_config,
        hanging_protocol,
        optional_hanging_protocols,
        view_content,
        display_editors,
        contact_email,
        workstation,
        inputs,
        outputs,
        structures,
        modalities,
        logo,
        user,
        phase,
        **kwargs,
    ):
        super().__init__(*args, user=user, phase=phase, **kwargs)
        self.fields["workstation_config"].initial = workstation_config
        self.fields["workstation_config"].disabled = True
        self.fields["hanging_protocol"].initial = hanging_protocol
        self.fields["hanging_protocol"].disabled = True
        self.fields["optional_hanging_protocols"].initial = (
            optional_hanging_protocols
        )
        self.fields["optional_hanging_protocols"].disabled = True
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
        self.fields["time_limit"].initial = phase.algorithm_time_limit
        self.fields["time_limit"].disabled = True

        self.fields["job_requires_gpu_type"].choices = [
            (choice.value, choice.label)
            for choice in GPUTypeChoices
            if choice in phase.algorithm_selectable_gpu_type_choices
        ]
        self.fields["job_requires_memory_gb"].validators = [
            MinValueValidator(settings.ALGORITHMS_MIN_MEMORY_GB),
            MaxValueValidator(phase.algorithm_maximum_settable_memory_gb),
        ]

    def clean(self):
        cleaned_data = super().clean()
        if (
            self.user_algorithm_count
            >= settings.ALGORITHMS_MAX_NUMBER_PER_USER_PER_PHASE
        ):
            raise ValidationError(
                "You have already created the maximum number of algorithms for this phase."
            )
        return cleaned_data


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
            "summary": MarkdownEditorInlineWidget,
            "mechanism": MarkdownEditorInlineWidget,
            "uses_and_directions": MarkdownEditorInlineWidget,
            "validation_and_performance": MarkdownEditorInlineWidget,
            "warnings": MarkdownEditorInlineWidget,
            "common_error_messages": MarkdownEditorInlineWidget,
            "editor_notes": MarkdownEditorInlineWidget,
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


class AlgorithmImageForm(ContainerImageForm):
    algorithm = ModelChoiceField(widget=HiddenInput(), queryset=None)

    def __init__(self, *args, algorithm, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["algorithm"].queryset = Algorithm.objects.filter(
            pk=algorithm.pk
        )
        self.fields["algorithm"].initial = algorithm

    class Meta(ContainerImageForm.Meta):
        model = AlgorithmImage
        fields = (
            "algorithm",
            *ContainerImageForm.Meta.fields,
        )


class AlgorithmImageUpdateForm(SaveFormInitMixin, ModelForm):
    class Meta:
        model = AlgorithmImage
        fields = ("comment",)


class ImageActivateForm(Form):
    algorithm_image = ModelChoiceField(queryset=AlgorithmImage.objects.none())

    def __init__(
        self,
        *args,
        user,
        algorithm,
        hide_algorithm_image_input=False,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.fields["algorithm_image"].queryset = (
            get_objects_for_user(
                user,
                "algorithms.change_algorithmimage",
            )
            .filter(
                algorithm=algorithm,
                is_manifest_valid=True,
                is_desired_version=False,
            )
            .select_related("algorithm")
        )

        if hide_algorithm_image_input:
            self.fields["algorithm_image"].widget = HiddenInput()

        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("save", "Activate algorithm image"))
        self.helper.form_action = reverse(
            "algorithms:image-activate", kwargs={"slug": algorithm.slug}
        )

    def clean_algorithm_image(self):
        algorithm_image = self.cleaned_data["algorithm_image"]

        if algorithm_image.algorithm.image_upload_in_progress:
            raise ValidationError("Image updating already in progress.")

        return algorithm_image


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

    def clean_public(self):
        public = self.cleaned_data["public"]
        if public and not self.instance.status == ComponentJob.SUCCESS:
            raise ValidationError(
                "You can only publish successful algorithm jobs."
            )
        return public


class DisplaySetFromJobForm(SaveFormInitMixin, Form):
    reader_study = ModelChoiceField(
        queryset=ReaderStudy.objects.none(), required=True
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["reader_study"].queryset = get_objects_for_user(
            user,
            "reader_studies.change_readerstudy",
        ).order_by("title")


class AlgorithmPermissionRequestUpdateForm(PermissionRequestUpdateForm):
    class Meta(PermissionRequestUpdateForm.Meta):
        model = AlgorithmPermissionRequest


class AlgorithmRepoForm(SaveFormInitMixin, ModelForm):
    repo_name = autocomplete.Select2ListCreateChoiceField(
        label="Repository Name",
        required=False,
        widget=autocomplete.ListSelect2(
            url="github:repositories-list",
            attrs={
                "data-placeholder": "No repository selected, search for a repository here...",
                "data-minimum-input-length": 3,
                "data-theme": settings.CRISPY_TEMPLATE_PACK,
            },
        ),
    )

    def __init__(self, *args, github_app_install_url, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.repo_name:
            self.fields["repo_name"].initial = self.instance.repo_name
            self.fields["repo_name"].choices = [
                (self.instance.repo_name, self.instance.repo_name),
            ]

        self.fields["repo_name"].help_text = format_html(
            (
                "If you cannot find your desired repository here please "
                "<a href='{}'>update the GitHub installation</a> "
                "and ensure the application has access to that repository, "
                "then refresh this page."
            ),
            github_app_install_url,
        )

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

    class Meta:
        model = Algorithm
        fields = (
            "repo_name",
            "recurse_submodules",
        )
        help_texts = {
            "recurse_submodules": (
                "Whether to recurse the git submodules when cloning your "
                "GitHub repository."
            ),
        }


class AlgorithmPublishForm(ModelForm):
    class Meta:
        model = Algorithm
        fields = ("public",)

    def clean_public(self):
        public = self.cleaned_data.get("public")
        if public and (
            not self.instance.contact_email
            or not self.instance.summary
            or not self.instance.public_test_case
            or not self.instance.mechanism
            or not self.instance.display_editors
        ):
            raise ValidationError(
                "To publish this algorithm you need at least 1 public test case with a successful result from the latest version of the algorithm. You also need a summary and description of the mechanism of your algorithm. The link to update your algorithm description can be found on the algorithm information page."
            )
        return public


class RemoteInstanceClient:
    def list_algorithms(self, netloc, slug, headers):
        url = urlparse(reverse(viewname="api:algorithm-list"))

        response = requests.get(
            url=url._replace(scheme="https", netloc=netloc).geturl(),
            params={"slug": slug},
            timeout=5,
            headers=headers,
        )

        if response.status_code != 200:
            raise ValidationError(
                f"{response.status_code} Response from {netloc}"
            )

        return response.json()

    def list_algorithm_images(self, netloc, algorithm_pk, headers):
        url = urlparse(reverse(viewname="api:algorithms-image-list"))

        response = requests.get(
            url=url._replace(scheme="https", netloc=netloc).geturl(),
            params={
                "algorithm": algorithm_pk,
            },
            timeout=5,
            headers=headers,
        )

        if response.status_code != 200:
            raise ValidationError(
                f"{response.status_code} Response from {netloc}"
            )

        return response.json()


class AlgorithmImportForm(SaveFormInitMixin, Form):
    algorithm_url = URLField(
        help_text=(
            "The URL of the detail view for the algorithm you want to import. "
            "You must be an editor of this algorithm."
        )
    )
    api_token = CharField(
        help_text=(
            "API token used to fetch the algorithm information from the "
            "remote instance. This will not be stored on the server."
        ),
        widget=PasswordInput(render_value=True),
    )
    remote_bucket_name = CharField(
        help_text=("The name of the remote bucket the image is stored on."),
        validators=[RegexValidator(regex=r"^[a-zA-Z0-9.\-_]{1,255}$")],
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.algorithm_serializer = None
        self.algorithm_image_serializer = None
        self.algorithm = None
        self.new_interfaces = None

    @property
    def remote_instance_client(self):
        return RemoteInstanceClient()

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data["api_token"]:
            headers = {"Authorization": f"BEARER {cleaned_data['api_token']}"}
        else:
            headers = {}

        parsed_algorithm_url = self._parse_remote_algorithm_url(
            cleaned_data["algorithm_url"]
        )
        algorithm_slug = parsed_algorithm_url["slug"]
        netloc = parsed_algorithm_url["netloc"]

        self._build_algorithm(
            algorithm_slug=algorithm_slug, headers=headers, netloc=netloc
        )
        self._build_algorithm_image(headers=headers, netloc=netloc)
        self._build_interfaces()

        return cleaned_data

    def _parse_remote_algorithm_url(self, url):
        parsed_url = urlparse(url)

        try:
            resolver_match = resolve(parsed_url.path)
        except Resolver404:
            raise ValidationError("Invalid URL")

        if resolver_match.view_name != "algorithms:detail":
            raise ValidationError("URL is not an algorithm detail view")

        return {
            "netloc": parsed_url.netloc,
            "slug": resolver_match.kwargs["slug"],
        }

    def clean_algorithm_url(self):
        algorithm_url = self.cleaned_data["algorithm_url"]

        if Algorithm.objects.filter(
            slug=self._parse_remote_algorithm_url(algorithm_url)["slug"]
        ).exists():
            raise ValidationError("An algorithm with that slug already exists")

        return algorithm_url

    def _build_algorithm(self, *, algorithm_slug, headers, netloc):
        algorithms_list = self.remote_instance_client.list_algorithms(
            slug=algorithm_slug, headers=headers, netloc=netloc
        )

        if algorithms_list["count"] != 1:
            raise ValidationError(
                f"Algorithm {algorithm_slug} not found, "
                "check your URL and API token."
            )

        algorithm_serializer = AlgorithmSerializer(
            data=algorithms_list["results"][0]
        )

        if not algorithm_serializer.is_valid():
            raise ValidationError("Algorithm is invalid")

        self.algorithm_serializer = algorithm_serializer

    def _build_algorithm_image(self, headers, netloc):
        algorithm_images_list = (
            self.remote_instance_client.list_algorithm_images(
                netloc=netloc,
                headers=headers,
                algorithm_pk=self.algorithm_serializer.initial_data["pk"],
            )
        )

        algorithm_images = [
            ai
            for ai in algorithm_images_list["results"]
            if ai["import_status"] == ImportStatusChoices.COMPLETED.label
        ]
        algorithm_images.sort(key=lambda ai: ai["created"], reverse=True)

        if len(algorithm_images) == 0:
            raise ValidationError(
                "No valid algorithm images found for this algorithm, "
                "check your URL and API token."
            )

        algorithm_image_serializer = AlgorithmImageSerializer(
            data=algorithm_images[0]
        )

        if not algorithm_image_serializer.is_valid():
            raise ValidationError("Algorithm image is invalid")

        self.algorithm_image_serializer = algorithm_image_serializer

    def _build_interfaces(self):
        remote_interfaces = {
            interface["slug"]: interface
            for interface in chain(
                self.algorithm_serializer.initial_data["inputs"],
                self.algorithm_serializer.initial_data["outputs"],
            )
        }

        self.new_interfaces = []
        for slug, remote_interface in remote_interfaces.items():
            try:
                self._validate_existing_interface(
                    slug=slug, remote_interface=remote_interface
                )
            except ObjectDoesNotExist:
                # The remote interface does not exist locally, create it
                self._create_new_interface(
                    slug=slug, remote_interface=remote_interface
                )

    def _validate_existing_interface(self, *, remote_interface, slug):
        serialized_local_interface = ComponentInterfaceSerializer(
            instance=ComponentInterface.objects.get(slug=slug)
        )

        for key, value in serialized_local_interface.data.items():
            # Check all the values match, some are allowed to differ
            if (
                key not in {"pk", "description"}
                and value != remote_interface[key]
            ):
                raise ValidationError(
                    f"Interface {key} does not match for `{slug}`"
                )

    def _create_new_interface(self, *, remote_interface, slug):
        new_interface = ComponentInterfaceSerializer(data=remote_interface)

        if not new_interface.is_valid():
            raise ValidationError(f"New interface {slug!r} is invalid")

        self.new_interfaces.append(new_interface)

    def save(self):
        self._save_new_interfaces()
        self._save_new_algorithm()
        self._save_new_algorithm_image()

    def _save_new_interfaces(self):
        for interface in self.new_interfaces:
            interface.save(
                # The interface kind is a read only display value, this could
                # be better solved with a custom DRF Field but deadlines...
                kind=get(
                    [
                        c[0]
                        for c in InterfaceKindChoices.choices
                        if c[1] == interface.initial_data["kind"]
                    ]
                ),
                store_in_database=False,
            )

            # Force the given slug to be used
            interface.instance.slug = interface.initial_data["slug"]

            # Set the store in database correctly, for most interfaces this is
            # False, then switch it if the super kind is different
            if interface.initial_data[
                "super_kind"
            ] != interface.get_super_kind(obj=interface.instance):
                interface.instance.store_in_database = True
            interface.instance.save()

    def _save_new_algorithm(self):
        self.algorithm = self.algorithm_serializer.save(
            pk=self.algorithm_serializer.initial_data["pk"],
        )
        self.algorithm.slug = self.algorithm_serializer.initial_data["slug"]

        self.algorithm.add_editor(user=self.user)

        self.algorithm.inputs.set(
            ComponentInterface.objects.filter(
                slug__in={
                    interface["slug"]
                    for interface in self.algorithm_serializer.initial_data[
                        "inputs"
                    ]
                }
            )
        )
        self.algorithm.outputs.set(
            ComponentInterface.objects.filter(
                slug__in={
                    interface["slug"]
                    for interface in self.algorithm_serializer.initial_data[
                        "outputs"
                    ]
                }
            )
        )

        if logo_url := self.algorithm_serializer.initial_data["logo"]:
            response = requests.get(
                url=logo_url, timeout=5, allow_redirects=True
            )
            logo = ContentFile(response.content)
            self.algorithm.logo.save(
                logo_url.rsplit("/")[-1].replace(".x20", ""), logo
            )

        original_url = self.algorithm_serializer.initial_data["url"]
        self.algorithm.summary += (
            f"\n\n#### Origin\n\nImported from "
            f"[{urlparse(original_url).netloc}]({original_url})."
        )
        self.algorithm.save()

    def _save_new_algorithm_image(self):
        algorithm_image = self.algorithm_image_serializer.save(
            algorithm=self.algorithm,
            pk=self.algorithm_image_serializer.initial_data["pk"],
            creator=self.user,
        )
        on_commit(
            import_remote_algorithm_image.signature(
                kwargs={
                    "algorithm_image_pk": algorithm_image.pk,
                    "remote_bucket_name": self.cleaned_data[
                        "remote_bucket_name"
                    ],
                }
            ).apply_async
        )


class AlgorithmModelForm(SaveFormInitMixin, ModelForm):
    algorithm = ModelChoiceField(widget=HiddenInput(), queryset=None)
    user_upload = ModelChoiceField(
        widget=UserUploadSingleWidget(
            allowed_file_types=[
                "application/x-gzip",
                "application/gzip",
            ]
        ),
        label="Algorithm Model",
        queryset=None,
        help_text=(
            ".tar.gz file of the algorithm model that will be extracted"
            " to /opt/ml/model/ during inference"
        ),
    )
    creator = ModelChoiceField(
        widget=HiddenInput(),
        queryset=(
            get_user_model()
            .objects.exclude(username=settings.ANONYMOUS_USER_NAME)
            .filter(verification__is_verified=True)
        ),
    )

    def __init__(self, *args, user, algorithm, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["user_upload"].queryset = get_objects_for_user(
            user,
            "uploads.change_userupload",
        ).filter(status=UserUpload.StatusChoices.COMPLETED)

        self.fields["creator"].initial = user
        self.fields["algorithm"].queryset = Algorithm.objects.filter(
            pk=algorithm.pk
        )
        self.fields["algorithm"].initial = algorithm

    def clean_creator(self):
        creator = self.cleaned_data["creator"]

        if AlgorithmModel.objects.filter(
            import_status=ImportStatusChoices.INITIALIZED,
            creator=creator,
        ).exists():
            self.add_error(
                None,
                "You have an existing model importing, please wait for it to complete",
            )

        return creator

    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)
        on_commit(
            assign_tarball_from_upload.signature(
                kwargs={
                    "app_label": instance._meta.app_label,
                    "model_name": instance._meta.model_name,
                    "tarball_pk": instance.pk,
                    "field_to_copy": "model",
                },
                immutable=True,
            ).apply_async
        )
        return instance

    class Meta:
        model = AlgorithmModel
        fields = ("algorithm", "user_upload", "creator", "comment")


class AlgorithmModelUpdateForm(SaveFormInitMixin, ModelForm):
    class Meta:
        model = AlgorithmModel
        fields = ("comment",)


class AlgorithmModelVersionControlForm(Form):
    algorithm_model = ModelChoiceField(queryset=AlgorithmModel.objects.none())

    def __init__(
        self,
        *args,
        user,
        algorithm,
        activate,
        hide_algorithm_model_input=False,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._activate = activate
        extra_filter = {}

        if activate:
            extra_filter = {"import_status": ImportStatusChoices.COMPLETED}

        self.fields["algorithm_model"].queryset = (
            get_objects_for_user(
                user,
                "algorithms.change_algorithmmodel",
            )
            .filter(
                algorithm=algorithm,
                is_desired_version=False if activate else True,
                **extra_filter,
            )
            .select_related("algorithm")
        )

        if hide_algorithm_model_input:

            self.fields["algorithm_model"].widget = HiddenInput()
        self.helper = FormHelper(self)
        if activate:
            self.helper.layout.append(
                Submit("save", "Activate algorithm model")
            )
            self.helper.form_action = reverse(
                "algorithms:model-activate", kwargs={"slug": algorithm.slug}
            )
        else:
            self.helper.layout.append(
                Submit("save", "Deactivate algorithm model")
            )
            self.helper.form_action = reverse(
                "algorithms:model-deactivate", kwargs={"slug": algorithm.slug}
            )

    def clean_algorithm_model(self):
        algorithm_model = self.cleaned_data["algorithm_model"]

        if (
            algorithm_model.get_peer_tarballs()
            .filter(import_status=ImportStatusChoices.INITIALIZED)
            .exists()
        ):
            raise ValidationError("Model updating already in progress.")

        return algorithm_model


class AlgorithmInterfaceForm(SaveFormInitMixin, ModelForm):
    inputs = ModelMultipleChoiceField(
        queryset=ComponentInterface.objects.exclude(
            slug__in=[*NON_ALGORITHM_INTERFACES, "results-json-file"]
        ),
        widget=Select2MultipleWidget,
    )
    outputs = ModelMultipleChoiceField(
        queryset=ComponentInterface.objects.exclude(
            slug__in=[*NON_ALGORITHM_INTERFACES, "results-json-file"]
        ),
        widget=Select2MultipleWidget,
    )
    set_as_default = BooleanField(required=False)

    class Meta:
        model = AlgorithmInterface
        fields = (
            "inputs",
            "outputs",
            "set_as_default",
        )

    def __init__(self, *args, algorithm, **kwargs):
        super().__init__(*args, **kwargs)
        self._algorithm = algorithm

        if not self._algorithm.default_interface:
            self.fields["set_as_default"].initial = True

    def clean_set_as_default(self):
        set_as_default = self.cleaned_data["set_as_default"]

        if not set_as_default and not self._algorithm.default_interface:
            raise ValidationError("Your algorithm needs a default interface.")

        return set_as_default

    def clean_inputs(self):
        inputs = self.cleaned_data.get("inputs", [])

        if not inputs:
            raise ValidationError("You must provide at least 1 input.")

        if (
            AlgorithmAlgorithmInterface.objects.filter(
                algorithm=self._algorithm
            )
            .annotate(
                input_count=Count("interface__inputs", distinct=True),
                relevant_input_count=Count(
                    "interface__inputs",
                    filter=Q(interface__inputs__in=inputs),
                    distinct=True,
                ),
            )
            .filter(input_count=len(inputs), relevant_input_count=len(inputs))
            .exists()
        ):
            raise ValidationError(
                "An AlgorithmInterface for this algorithm with the "
                "same inputs already exists. "
                "Algorithm interfaces need to have unique sets of inputs."
            )
        return inputs

    def clean_outputs(self):
        outputs = self.cleaned_data.get("outputs", [])

        if not outputs:
            raise ValidationError("You must provide at least 1 output.")

        return outputs

    def clean(self):
        cleaned_data = super().clean()

        # there should always be at least one input and one output,
        # this is checked in the individual fields clean methods
        inputs = cleaned_data.get("inputs")
        outputs = cleaned_data.get("outputs")

        # if either of the two fields is not provided, no need to check for
        # duplicates here
        if inputs and outputs:
            duplicate_interfaces = {*inputs}.intersection({*outputs})

            if duplicate_interfaces:
                raise ValidationError(
                    f"The sets of Inputs and Outputs must be unique: "
                    f"{oxford_comma(duplicate_interfaces)} present in both"
                )

        return cleaned_data

    def save(self):
        interface = AlgorithmInterface.objects.create(
            inputs=self.cleaned_data["inputs"],
            outputs=self.cleaned_data["outputs"],
        )

        if self.cleaned_data["set_as_default"]:
            AlgorithmAlgorithmInterface.objects.filter(
                algorithm=self._algorithm
            ).update(is_default=False)

        matched_rows = AlgorithmAlgorithmInterface.objects.filter(
            algorithm=self._algorithm, interface=interface
        ).update(is_default=self.cleaned_data["set_as_default"])

        if matched_rows == 0:
            self._algorithm.interfaces.add(
                interface,
                through_defaults={
                    "is_default": self.cleaned_data["set_as_default"]
                },
            )
        elif matched_rows > 1:
            raise RuntimeError(
                "This algorithm and interface are associated "
                "with each other more than once."
            )

        return interface


class JobInterfaceSelectForm(SaveFormInitMixin, Form):
    algorithm_interface = ModelChoiceField(
        queryset=None,
        required=True,
        help_text="Select an input-output combination to use for this job.",
        widget=RadioSelect,
    )

    def __init__(self, *args, algorithm, **kwargs):
        super().__init__(*args, **kwargs)

        self._algorithm = algorithm

        self.fields["algorithm_interface"].queryset = (
            self._algorithm.interfaces.all()
        )
        self.fields["algorithm_interface"].initial = (
            self._algorithm.default_interface
        )
        self.fields["algorithm_interface"].widget.choices = {
            (
                interface.pk,
                format_html(
                    "<div><b>Inputs</b>: {inputs}</div>"
                    "<div class='mb-3'><b>Outputs</b>: {outputs}</div>",
                    inputs=oxford_comma(interface.inputs.all()),
                    outputs=oxford_comma(interface.outputs.all()),
                ),
            )
            for interface in self._algorithm.interfaces.all()
        }
