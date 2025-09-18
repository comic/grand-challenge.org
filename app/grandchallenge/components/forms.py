import logging

from crispy_forms.helper import FormHelper
from crispy_forms.layout import ButtonHolder, Layout, Submit
from dal import autocomplete
from dal.widgets import Select
from django.conf import settings
from django.contrib.auth import get_user_model
from django.forms import (
    CheckboxSelectMultiple,
    Form,
    HiddenInput,
    ModelChoiceField,
    ModelForm,
    ModelMultipleChoiceField,
)
from django.utils.functional import empty
from django.utils.text import format_lazy

from grandchallenge.algorithms.models import AlgorithmImage
from grandchallenge.cases.widgets import (
    DICOMUploadWidgetSuffixes,
    DICOMUploadWithName,
)
from grandchallenge.components.backends.exceptions import (
    CIVNotEditableException,
)
from grandchallenge.components.form_fields import (
    INTERFACE_FORM_FIELD_PREFIX,
    InterfaceFormFieldFactory,
)
from grandchallenge.components.models import CIVData, ComponentInterface
from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.core.guardian import filter_by_permission
from grandchallenge.evaluation.models import Method
from grandchallenge.subdomains.utils import reverse_lazy
from grandchallenge.uploads.models import UserUpload
from grandchallenge.uploads.widgets import UserUploadSingleWidget
from grandchallenge.workstations.models import WorkstationImage

logger = logging.getLogger(__name__)


class ContainerImageForm(SaveFormInitMixin, ModelForm):
    user_upload = ModelChoiceField(
        widget=UserUploadSingleWidget(
            allowed_file_types=[
                "application/x-tar",
                "application/x-gzip",
                "application/gzip",
                "application/x-xz",
                "application/octet-stream",
            ]
        ),
        label="Container Image",
        queryset=None,
        help_text=(
            ".tar.gz archive of the container image produced from the command "
            "'docker save IMAGE | gzip -c > IMAGE.tar.gz'. See "
            "https://docs.docker.com/engine/reference/commandline/save/"
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

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["user_upload"].queryset = filter_by_permission(
            queryset=UserUpload.objects.filter(
                status=UserUpload.StatusChoices.COMPLETED
            ),
            user=user,
            codename="change_userupload",
        )

        self.fields["creator"].initial = user

    def clean_creator(self):
        creator = self.cleaned_data["creator"]

        for model in (AlgorithmImage, Method, WorkstationImage):
            if model.objects.filter(
                import_status__in=[
                    model.ImportStatusChoices.INITIALIZED,
                    model.ImportStatusChoices.QUEUED,
                    model.ImportStatusChoices.STARTED,
                ],
                creator=creator,
            ).exists():
                self.add_error(
                    None,
                    (
                        "You have an existing container image importing, "
                        "please wait for it to complete"
                    ),
                )
                break

        return creator

    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)
        instance.assign_docker_image_from_upload()
        return instance

    class Meta:
        fields = ("user_upload", "creator", "comment")


class AdditionalInputsMixin:
    def init_additional_inputs(self, *, inputs):
        for input in inputs:
            prefixed_interface_slug = (
                f"{INTERFACE_FORM_FIELD_PREFIX}{input.slug}"
            )

            if prefixed_interface_slug in self.data:
                try:
                    initial = self.data.getlist(prefixed_interface_slug)
                    if len(initial) == 1:
                        initial = initial[0]
                except AttributeError:
                    initial = self.data.get(prefixed_interface_slug)
            else:
                initial = None

            self.fields[prefixed_interface_slug] = InterfaceFormFieldFactory(
                interface=input,
                user=self._user,
                required=input.value_required,
                initial=initial if initial else input.default_value,
            )

    def clean_additional_inputs(self):
        keys_to_remove = []
        inputs = []

        for key, value in self.cleaned_data.items():
            if key.startswith(INTERFACE_FORM_FIELD_PREFIX):
                keys_to_remove.append(key)
                inputs.append(
                    CIVData(
                        interface_slug=key[len(INTERFACE_FORM_FIELD_PREFIX) :],
                        value=value,
                    )
                )

        for key in keys_to_remove:
            self.cleaned_data.pop(key)

        return inputs


class MultipleCIVForm(Form):
    possible_widgets = InterfaceFormFieldFactory.possible_widgets

    def __init__(self, *args, instance, base_obj, user, **kwargs):  # noqa C901
        super().__init__(*args, **kwargs)
        self.instance = instance
        self.user = user
        self.base_obj = base_obj

        # add fields for all interfaces that already exist on
        # other display sets / archive items
        for slug in base_obj.values_for_interfaces.keys():
            current_value = None

            interface = ComponentInterface.objects.filter(slug=slug).get()
            prefixed_interface_slug = f"{INTERFACE_FORM_FIELD_PREFIX}{slug}"

            if prefixed_interface_slug in self.data:
                try:
                    current_value = self.data.getlist(prefixed_interface_slug)
                    if len(current_value) == 1:
                        current_value = current_value[0]
                except AttributeError:
                    current_value = self.data.get(prefixed_interface_slug)

            if not current_value and instance:
                current_value = instance.values.filter(
                    interface__slug=slug
                ).first()

            self.fields[prefixed_interface_slug] = InterfaceFormFieldFactory(
                interface=interface,
                user=self.user,
                required=False,
                initial=current_value,
            )

        # Add fields for dynamically added new interfaces
        self.interface_data_map = self.group_form_data_by_interface_slug()

        for interface, data in self.interface_data_map.items():
            try:
                initial = data.get("value")
            except KeyError:
                initial = DICOMUploadWithName(
                    name=data.get(DICOMUploadWidgetSuffixes[0]),
                    user_uploads=data.get(DICOMUploadWidgetSuffixes[1]),
                )

            self.fields[data.get("field_name")] = InterfaceFormFieldFactory(
                interface=interface,
                user=self.user,
                required=False,
                initial=initial,
            )

    @staticmethod
    def parse_slug(*, slug):
        """
        Return (base_slug, suffix) given a full form slug.
        If no known suffix is found, suffix is None.
        """
        # remove prefix
        interface_slug = slug[len(INTERFACE_FORM_FIELD_PREFIX) :]

        # separate known suffix
        for known_suffix in DICOMUploadWidgetSuffixes:
            if known_suffix in interface_slug:
                base_slug = interface_slug.split(f"_{known_suffix}", 1)[0]
                return base_slug, known_suffix

        return interface_slug, None

    def group_form_data_by_interface_slug(self):
        interface_data_map = {}

        # Extract relevant slugs
        slug_info = {}
        candidate_slugs = set()

        for slug in self.data.keys():
            if (
                not slug.startswith(INTERFACE_FORM_FIELD_PREFIX)
                or slug in self.fields
            ):
                # we only care about dynamically added interface fields,
                # i.e. fields that start with the relevant prefix and
                # that do not have a field on the form yet (as defined through
                # sockets attached to other items from the same base object)
                continue

            base_slug, suffix = self.parse_slug(slug=slug)
            slug_info[slug] = (base_slug, suffix)
            candidate_slugs.add(base_slug)

        # Fetch all interfaces in one go
        interfaces_by_slug = {
            ci.slug: ci
            for ci in ComponentInterface.objects.filter(
                slug__in=candidate_slugs
            )
        }

        for slug, (base_slug, suffix) in slug_info.items():

            if not (interface := interfaces_by_slug.get(base_slug)):
                # only existing sockets should be processed further
                continue

            try:
                value = self.data.getlist(slug)
                if len(value) == 1:
                    value = value[0]
            except AttributeError:
                value = self.data.get(slug)

            key = suffix or "value"
            if interface not in interface_data_map.keys():
                interface_data_map[interface] = {
                    key: value,
                    "field_name": f"{INTERFACE_FORM_FIELD_PREFIX}{base_slug}",
                }
            else:
                interface_data_map[interface][key] = value

        return interface_data_map

    def process_object_data(self):
        civs = []
        for key, value in self.cleaned_data.items():
            if key.startswith(INTERFACE_FORM_FIELD_PREFIX):
                civs.append(
                    CIVData(
                        interface_slug=key[len(INTERFACE_FORM_FIELD_PREFIX) :],
                        value=value,
                    )
                )

        try:
            self.instance.validate_values_and_execute_linked_task(
                values=civs,
                user=self.user,
            )
        except CIVNotEditableException as e:
            error_handler = self.instance.get_error_handler()
            error_handler.handle_error(
                error_message="An unexpected error occurred", user=self.user
            )
            logger.error(e, exc_info=True)


class CIVSetCreateFormMixin:
    instance = None

    def process_object_data(self):
        non_civ_data = {
            k: v
            for k, v in self.cleaned_data.items()
            if not k.startswith(INTERFACE_FORM_FIELD_PREFIX)
        }
        self.instance = self.base_obj.create_civ_set(data=non_civ_data)
        super().process_object_data()


class CIVSetUpdateFormMixin:
    def process_object_data(self):
        instance = self.instance

        save = False
        for key in self.cleaned_data.keys():
            if not key.startswith(INTERFACE_FORM_FIELD_PREFIX):
                value = self.cleaned_data.get(key, empty)
                if value is not empty and value != getattr(instance, key):
                    setattr(instance, key, value)
                    save = True
        if save:
            instance.save()

        super().process_object_data()


class SingleCIVForm(Form):
    possible_widgets = {
        *InterfaceFormFieldFactory.possible_widgets,
        autocomplete.ModelSelect2,
        Select,
    }

    def __init__(
        self,
        *args,
        pk,
        interface,
        base_obj,
        user,
        htmx_url,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        data = kwargs.get("data")

        try:
            socket_filter_kwargs = {"slug__in": base_obj.allowed_socket_slugs}
        except AttributeError:
            socket_filter_kwargs = {}

        qs = (
            ComponentInterface.objects.all()
            .filter(**socket_filter_kwargs)
            .exclude(slug__in=base_obj.values_for_interfaces.keys())
        )

        if interface:
            selected_interface = ComponentInterface.objects.get(pk=interface)
        elif data and data.get("interface"):
            selected_interface = ComponentInterface.objects.get(
                pk=data["interface"]
            )
        else:
            selected_interface = None

        widget_kwargs = {}
        attrs = {
            "hx-get": htmx_url,
            "hx-trigger": "interfaceSelected",
            "disabled": selected_interface is not None,
            "hx-target": f"#form-{kwargs['auto_id']}",
            "hx-swap": "outerHTML",
            "hx-include": "this",
        }

        if selected_interface:
            widget = Select
            interface_field_name = "interface"
        else:
            widget = autocomplete.ModelSelect2
            attrs.update(
                {
                    "data-placeholder": "Search for a socket ...",
                    "data-minimum-input-length": 3,
                    "data-theme": settings.CRISPY_TEMPLATE_PACK,
                    "data-html": True,
                }
            )
            widget_kwargs["url"] = (
                "components:component-interface-autocomplete"
            )
            interface_field_name = f"interface-{kwargs['auto_id']}"
            widget_kwargs["forward"] = [interface_field_name]
        widget_kwargs["attrs"] = attrs

        self.fields[interface_field_name] = ModelChoiceField(
            initial=selected_interface,
            queryset=qs,
            widget=widget(**widget_kwargs),
            label="Socket",
            help_text=format_lazy(
                (
                    'See the <a href="{}">list of sockets</a> for more '
                    "information about each socket. "
                    "Please contact support if your desired socket is missing."
                ),
                reverse_lazy(base_obj.interface_viewname),
            ),
        )

        if selected_interface is not None:
            self.fields[
                f"{INTERFACE_FORM_FIELD_PREFIX}{selected_interface.slug}"
            ] = InterfaceFormFieldFactory(
                interface=selected_interface,
                user=user,
                required=selected_interface.value_required,
            )


class CIVSetDeleteForm(Form):
    civ_sets_to_delete = ModelMultipleChoiceField(
        queryset=None,
        label="",
        widget=CheckboxSelectMultiple,
    )

    def __init__(self, *args, queryset, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        # prepend button since the list of objects can be long
        self.helper.layout = Layout(
            ButtonHolder(
                Submit(
                    "save",
                    "Yes, I confirm that I want to delete all of the below selected items.",
                    css_class="border-danger bg-danger mb-3",
                )
            ),
            "civ_sets_to_delete",
        )

        self.fields["civ_sets_to_delete"].queryset = queryset
        self.fields["civ_sets_to_delete"].initial = queryset
