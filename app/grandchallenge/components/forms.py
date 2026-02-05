import logging
from enum import StrEnum

from crispy_forms.helper import FormHelper
from crispy_forms.layout import ButtonHolder, Layout, Submit
from dal import autocomplete
from dal.widgets import Select
from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
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
from grandchallenge.cases.form_fields import (
    DICOMUploadField,
    ImageSearchMultiField,
    ImageSourceChoiceField,
)
from grandchallenge.cases.forms import IMAGE_UPLOAD_HELP_TEXT
from grandchallenge.cases.widgets import ImageSearchInputWidget
from grandchallenge.components.backends.exceptions import (
    CIVNotEditableException,
)
from grandchallenge.components.form_fields import (
    BoundFieldWithDNoneClass,
    FileSearchMultiField,
    FileSourceChoiceField,
)
from grandchallenge.components.models import (
    RESERVED_SOCKET_SLUGS,
    CIVData,
    ComponentInterface,
    SourceChoices,
)
from grandchallenge.components.schemas import generate_component_json_schema
from grandchallenge.components.widgets import (
    FileSearchInputWidget,
    SearchSelect,
    SourceSelect,
)
from grandchallenge.core.forms import SaveFormInitMixin, UserMixin
from grandchallenge.core.guardian import filter_by_permission
from grandchallenge.core.templatetags.bleach import clean
from grandchallenge.core.validators import JSONValidator
from grandchallenge.core.widgets import JSONEditorWidget
from grandchallenge.evaluation.models import Method
from grandchallenge.subdomains.utils import reverse_lazy
from grandchallenge.uploads.models import UserUpload
from grandchallenge.uploads.widgets import (
    DICOMUserUploadMultipleWidget,
    UserUploadMultipleWidget,
    UserUploadSingleWidget,
)
from grandchallenge.workstations.models import WorkstationImage

logger = logging.getLogger(__name__)


FILE_UPLOAD_HELP_TEXT = (
    "The total size of all files uploaded in a single session "
    "cannot exceed 10 GB.<br>"
    "The following file formats are supported: "
)


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


INTERFACE_FORM_FIELD_PREFIX = "__INTERFACE_FIELD__"


class FlexibleWidgetPrefixes(StrEnum):
    CHOICE = f"flexible_widget_choice{INTERFACE_FORM_FIELD_PREFIX}"
    UPLOAD = f"flexible_upload{INTERFACE_FORM_FIELD_PREFIX}"
    SEARCH = f"flexible_search{INTERFACE_FORM_FIELD_PREFIX}"


class InterfaceFormFieldsMixin:
    possible_widgets = {
        UserUploadMultipleWidget,
        UserUploadSingleWidget,
        DICOMUserUploadMultipleWidget,
        JSONEditorWidget,
        FileSearchInputWidget,
        ImageSearchInputWidget,
        SearchSelect,
        SourceSelect,
    }

    def get_fields_for_interface(
        self,
        *,
        interface,
        user=None,
        required=True,
        current_socket_value=None,
        disabled=False,
    ):
        prefixed_interface_slug = (
            f"{INTERFACE_FORM_FIELD_PREFIX}{interface.slug}"
        )

        kwargs = {
            "required": required,
            "help_text": clean(interface.description),
            "disabled": disabled,
            "label": interface.title.title(),
        }

        if interface.super_kind == interface.SuperKind.IMAGE:
            if interface.is_dicom_image_kind:
                upload_field = DICOMUploadField(
                    user=user,
                    label="",
                    required=False,
                    bound_field_class=BoundFieldWithDNoneClass,
                )
            else:
                upload_field = ModelMultipleChoiceField(
                    queryset=filter_by_permission(
                        queryset=UserUpload.objects.all(),
                        user=user,
                        codename="change_userupload",
                    ).filter(status=UserUpload.StatusChoices.COMPLETED),
                    widget=UserUploadMultipleWidget,
                    label="",
                    help_text=IMAGE_UPLOAD_HELP_TEXT,
                    required=False,
                    bound_field_class=BoundFieldWithDNoneClass,
                )
            return {
                f"{FlexibleWidgetPrefixes.CHOICE}{interface.slug}": ImageSourceChoiceField(
                    current_socket_value=current_socket_value,
                    **kwargs,
                ),
                f"{FlexibleWidgetPrefixes.UPLOAD}{interface.slug}": upload_field,
                f"{FlexibleWidgetPrefixes.SEARCH}{interface.slug}": ImageSearchMultiField(
                    user=user,
                    interface=interface,
                    prefixed_interface_slug=prefixed_interface_slug,
                    label="",
                    required=False,
                    bound_field_class=BoundFieldWithDNoneClass,
                ),
            }
        elif interface.super_kind == interface.SuperKind.FILE:
            return {
                f"{FlexibleWidgetPrefixes.CHOICE}{interface.slug}": FileSourceChoiceField(
                    current_socket_value=current_socket_value,
                    **kwargs,
                ),
                f"{FlexibleWidgetPrefixes.UPLOAD}{interface.slug}": ModelChoiceField(
                    queryset=filter_by_permission(
                        queryset=UserUpload.objects.all(),
                        user=user,
                        codename="change_userupload",
                    ).filter(status=UserUpload.StatusChoices.COMPLETED),
                    widget=UserUploadSingleWidget,
                    label="",
                    help_text=f"{FILE_UPLOAD_HELP_TEXT} {interface.file_extension}",
                    required=False,
                    bound_field_class=BoundFieldWithDNoneClass,
                ),
                f"{FlexibleWidgetPrefixes.SEARCH}{interface.slug}": FileSearchMultiField(
                    user=user,
                    interface=interface,
                    prefixed_interface_slug=prefixed_interface_slug,
                    label="",
                    required=False,
                    bound_field_class=BoundFieldWithDNoneClass,
                ),
            }
        elif interface.super_kind == interface.SuperKind.VALUE:
            return {
                prefixed_interface_slug: self.get_json_field(
                    interface=interface,
                    current_socket_value=current_socket_value,
                    **kwargs,
                )
            }
        else:
            raise NotImplementedError(
                f"Unknown interface super kind: {interface.super_kind}"
            )

    @staticmethod
    def get_json_field(interface, current_socket_value, **kwargs):
        if current_socket_value is not None:
            kwargs["initial"] = current_socket_value.value
        else:
            kwargs["initial"] = interface.default_value

        field_type = interface.default_field

        schema = generate_component_json_schema(
            component_interface=interface,
            required=kwargs["required"],
        )

        if field_type == forms.JSONField:
            kwargs["widget"] = JSONEditorWidget(schema=schema)
        kwargs["validators"] = [JSONValidator(schema=schema)]

        return field_type(**kwargs)

    def full_clean(self):
        # Mark selected widgets as required for validation
        fields_required = {}

        try:
            for name in self.fields:
                if name.startswith(FlexibleWidgetPrefixes.CHOICE):
                    interface_slug = name[len(FlexibleWidgetPrefixes.CHOICE) :]
                    choice = self[name].data

                    widget_fields = {
                        SourceChoices.SEARCH: f"{FlexibleWidgetPrefixes.SEARCH}{interface_slug}",
                        SourceChoices.UPLOAD: f"{FlexibleWidgetPrefixes.UPLOAD}{interface_slug}",
                    }

                    for widget_type, field_name in widget_fields.items():
                        if choice == widget_type:
                            # Store original required state and temporarily set to required
                            fields_required[field_name] = self[
                                field_name
                            ].field.required
                            self[field_name].field.required = True

            super().full_clean()
        finally:
            # Reset `required` to avoid javascript validation.
            # Items may otherwise get a "Please fill out this field" tooltip
            # blocking submission. This will lead to issues if this field is no
            # longer the selected choice. (The widget is then not focusable.)
            for field_name, required in fields_required.items():
                self[field_name].field.required = required

    def clean(self):
        cleaned_data = super().clean()

        keys_to_remove = []
        data_to_add = {}

        for key in cleaned_data.keys():
            if any(
                [
                    key.startswith(prefix.value)
                    for prefix in FlexibleWidgetPrefixes
                ]
            ):
                keys_to_remove.append(key)

            if key.startswith(FlexibleWidgetPrefixes.CHOICE):
                # Get the choice from the field data because if it is "CURRENT"
                # the cleaned data becomes the current socket value (image)
                choice = self[key].data
                interface_slug = key[len(FlexibleWidgetPrefixes.CHOICE) :]
                prefixed_interface_slug = (
                    f"{INTERFACE_FORM_FIELD_PREFIX}{interface_slug}"
                )
                widget_fields = {
                    SourceChoices.CURRENT: key,
                    SourceChoices.REMOVE: key,
                    SourceChoices.SEARCH: f"{FlexibleWidgetPrefixes.SEARCH}{interface_slug}",
                    SourceChoices.UPLOAD: f"{FlexibleWidgetPrefixes.UPLOAD}{interface_slug}",
                }

                for widget_type, field_name in widget_fields.items():
                    if choice == widget_type:
                        try:
                            data_to_add[prefixed_interface_slug] = (
                                cleaned_data[field_name]
                            )
                        except KeyError:
                            pass
                    else:
                        if (
                            widget_type
                            in [SourceChoices.SEARCH, SourceChoices.UPLOAD]
                            and field_name in self.errors
                        ):
                            # Ignore errors if it is not the selected choice.
                            del self._errors[field_name]

        cleaned_data.update(data_to_add)

        for key in keys_to_remove:
            del cleaned_data[key]

        return cleaned_data


class AdditionalInputsMixin(UserMixin, InterfaceFormFieldsMixin):

    def __init__(self, *args, additional_inputs, **kwargs):
        self._additional_inputs = additional_inputs

        super().__init__(*args, **kwargs)

        for interface in self._additional_inputs:
            self.fields.update(
                self.get_fields_for_interface(
                    interface=interface,
                    user=self._user,
                    required=interface.value_required,
                )
            )

    def clean(self):
        cleaned_data = super().clean()

        keys_to_remove = []
        inputs = []
        # Cannot call add_error in the for-loop because it updates cleaned_data,
        # so save errors to call add_error later.
        errors = {}

        for key, value in cleaned_data.items():
            if key.startswith(INTERFACE_FORM_FIELD_PREFIX):
                keys_to_remove.append(key)
                try:
                    civ_data = CIVData(
                        interface_slug=key[len(INTERFACE_FORM_FIELD_PREFIX) :],
                        value=value,
                    )
                except ValidationError as error:
                    errors[key] = error
                else:
                    inputs.append(civ_data)

        for key in keys_to_remove:
            cleaned_data.pop(key)

        for key, error in errors.items():
            self.add_error(key, error)

        cleaned_data["additional_inputs"] = inputs

        return cleaned_data


class MultipleCIVForm(InterfaceFormFieldsMixin, Form):
    def __init__(self, *args, instance, base_obj, user, **kwargs):  # noqa C901
        super().__init__(*args, **kwargs)
        self.instance = instance
        self.user = user
        self.base_obj = base_obj

        # add fields for all interfaces that already exist on
        # other display sets / archive items
        for interface in base_obj.linked_component_interfaces.order_by(
            "title"
        ):
            if instance:
                current_socket_value = instance.values.filter(
                    interface__slug=interface.slug
                ).first()
            else:
                current_socket_value = None

            self.fields.update(
                self.get_fields_for_interface(
                    interface=interface,
                    user=self.user,
                    required=False,
                    current_socket_value=current_socket_value,
                )
            )

        for interface in self.get_dynamically_added_interfaces():
            self.fields.update(
                self.get_fields_for_interface(
                    interface=interface,
                    user=self.user,
                    required=False,
                )
            )

    def get_dynamically_added_interfaces(self):
        new_interface_slugs = set()
        for field_name in self.data.keys():
            interface_slug = self.get_interface_slug(field_name=field_name)

            if interface_slug and field_name not in self.fields.keys():
                new_interface_slugs.add(interface_slug)

        return ComponentInterface.objects.filter(slug__in=new_interface_slugs)

    @staticmethod
    def get_interface_slug(*, field_name):
        if field_name.startswith(INTERFACE_FORM_FIELD_PREFIX):
            interface_slug = field_name[len(INTERFACE_FORM_FIELD_PREFIX) :]
        elif field_name.startswith(FlexibleWidgetPrefixes.CHOICE):
            interface_slug = field_name[len(FlexibleWidgetPrefixes.CHOICE) :]
        else:
            interface_slug = None
        return interface_slug

    def clean(self):
        cleaned_data = super().clean()

        keys_to_remove = []
        inputs = []
        # Cannot call add_error in the for-loop because it updates cleaned_data,
        # so save errors to call add_error later.
        errors = {}

        for key, value in cleaned_data.items():
            if key.startswith(INTERFACE_FORM_FIELD_PREFIX):
                keys_to_remove.append(key)
                interface_slug = key[len(INTERFACE_FORM_FIELD_PREFIX) :]

                try:
                    if (
                        interface_slug
                        not in self.base_object.allowed_socket_slugs
                    ):
                        errors[key] = ValidationError(
                            f"Socket {interface_slug} is not allowed "
                            f"for this {self.base_object._meta.model_name}."
                        )
                        continue
                except AttributeError:
                    pass

                try:
                    civ_data = CIVData(
                        interface_slug=interface_slug,
                        value=value,
                    )
                except ValidationError as error:
                    errors[key] = error
                else:
                    inputs.append(civ_data)

        for key in keys_to_remove:
            cleaned_data.pop(key)

        for key, error in errors.items():
            self.add_error(key, error)

        # Mark as CIV data and not base-object data
        cleaned_data[INTERFACE_FORM_FIELD_PREFIX + "civ_data_objects"] = inputs

        return cleaned_data

    def process_object_data(self):
        civ_data_objects = self.cleaned_data.pop(
            INTERFACE_FORM_FIELD_PREFIX + "civ_data_objects"
        )

        try:
            self.instance.process_civ_data_objects_and_execute_linked_task(
                civ_data_objects=civ_data_objects, user=self.user
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
    def clean(self):
        if not self.instance.is_editable:
            raise ValidationError(self.instance.not_editable_error_message)

        return super().clean()

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


class SingleCIVForm(InterfaceFormFieldsMixin, Form):
    possible_widgets = {
        *InterfaceFormFieldsMixin.possible_widgets,
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
        form_id,
        htmx_url,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.form_id = form_id
        data = kwargs.get("data")

        try:
            socket_filter_kwargs = {"slug__in": base_obj.allowed_socket_slugs}
        except AttributeError:
            socket_filter_kwargs = {}

        qs = (
            ComponentInterface.objects.all()
            .filter(**socket_filter_kwargs)
            .exclude(
                slug__in={
                    *base_obj.linked_component_interfaces.values_list(
                        "slug", flat=True
                    ),
                    *RESERVED_SOCKET_SLUGS,
                }
            )
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
            "hx-target": f"#form-{form_id}",
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
            interface_field_name = f"interface-{form_id}"
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
            self.fields.update(
                self.get_fields_for_interface(
                    interface=selected_interface,
                    user=user,
                    required=selected_interface.value_required,
                )
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
