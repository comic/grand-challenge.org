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
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.files.base import ContentFile
from django.core.validators import RegexValidator
from django.db.transaction import on_commit
from django.forms import (
    CharField,
    ChoiceField,
    Form,
    HiddenInput,
    IntegerField,
    ModelChoiceField,
    ModelForm,
    ModelMultipleChoiceField,
    Select,
    TextInput,
    URLField,
)
from django.forms.widgets import MultipleHiddenInput, PasswordInput
from django.urls import Resolver404, resolve
from django.utils.html import format_html
from django.utils.text import format_lazy
from django_select2.forms import Select2MultipleWidget

from grandchallenge.algorithms.models import (
    Algorithm,
    AlgorithmImage,
    AlgorithmPermissionRequest,
    Job,
)
from grandchallenge.algorithms.serializers import (
    AlgorithmImageSerializer,
    AlgorithmSerializer,
)
from grandchallenge.algorithms.tasks import import_remote_algorithm_image
from grandchallenge.components.form_fields import InterfaceFormField
from grandchallenge.components.forms import ContainerImageForm
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentJob,
    ImportStatusChoices,
    InterfaceKindChoices,
)
from grandchallenge.components.serializers import ComponentInterfaceSerializer
from grandchallenge.core.forms import (
    PermissionRequestUpdateForm,
    SaveFormInitMixin,
    WorkstationUserFilterMixin,
)
from grandchallenge.core.guardian import get_objects_for_user
from grandchallenge.core.templatetags.bleach import clean
from grandchallenge.core.templatetags.remove_whitespace import oxford_comma
from grandchallenge.core.widgets import MarkdownEditorWidget
from grandchallenge.evaluation.utils import get
from grandchallenge.groups.forms import UserGroupForm
from grandchallenge.hanging_protocols.forms import ViewContentMixin
from grandchallenge.reader_studies.models import ReaderStudy
from grandchallenge.subdomains.utils import reverse, reverse_lazy
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
                instance=inp,
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
            "inputs",
            "outputs",
            "workstation",
            "workstation_config",
            "hanging_protocol",
            "view_content",
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

    def clean_public(self):
        public = self.cleaned_data["public"]
        if public and not self.instance.status == ComponentJob.SUCCESS:
            return ValidationError(
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


class AlgorithmRepoForm(RepoNameValidationMixin, SaveFormInitMixin, ModelForm):
    repo_name = ChoiceField()

    def __init__(self, *args, **kwargs):
        repos = kwargs.pop("repos")
        super().__init__(*args, **kwargs)
        self.fields["repo_name"].choices = [(repo, repo) for repo in repos]

    class Meta:
        model = Algorithm
        fields = ("repo_name",)


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
        self.algorithm.detail_page_markdown += (
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
