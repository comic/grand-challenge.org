from dal import autocomplete
from dal.widgets import Select
from django.conf import settings
from django.contrib.auth import get_user_model
from django.forms import Form, HiddenInput, ModelChoiceField, ModelForm

from grandchallenge.algorithms.models import AlgorithmImage
from grandchallenge.components.form_fields import InterfaceFormField
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.core.guardian import get_objects_for_user
from grandchallenge.evaluation.models import Method
from grandchallenge.uploads.models import UserUpload
from grandchallenge.uploads.widgets import UserUploadSingleWidget
from grandchallenge.workstations.models import WorkstationImage


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
            ".tar.xz archive of the container image produced from the command "
            "'docker save IMAGE | xz -T0 -c > IMAGE.tar.xz'. See "
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

        self.fields["user_upload"].queryset = get_objects_for_user(
            user,
            "uploads.change_userupload",
        ).filter(status=UserUpload.StatusChoices.COMPLETED)

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


class MultipleCIVForm(Form):
    _possible_widgets = {
        *InterfaceFormField._possible_widgets,
    }

    def __init__(self, *args, instance, base_obj, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = instance
        self.user = user
        self.base_obj = base_obj

        # add fields for all interfaces that already exist on
        # other display sets / archive items
        for slug, values in base_obj.values_for_interfaces.items():
            current_value = None

            if instance:
                current_value = instance.values.filter(
                    interface__slug=slug
                ).first()

            self.init_interface_field(
                interface_slug=slug, current_value=current_value, values=values
            )
        # Add fields for dynamically added new interfaces:
        # These are sent along as form data like all other fields, so we can't
        # tell them apart from the form fields initialized above. Hence
        # the check if they already have a corresponding field on the form or not.
        for slug in self.data.keys():
            if (
                ComponentInterface.objects.filter(slug=slug).exists()
                and slug not in self.fields.keys()
            ):
                self.init_interface_field(
                    interface_slug=slug,
                    current_value=None,
                    values=[],
                )

    def init_interface_field(self, interface_slug, current_value, values):
        interface = ComponentInterface.objects.get(slug=interface_slug)
        if interface.is_image_kind:
            self.fields[interface_slug] = self._get_image_field(
                interface=interface,
                current_value=current_value,
            )
        elif interface.requires_file:
            self.fields[interface_slug] = self._get_file_field(
                interface=interface,
                values=values,
                current_value=current_value,
            )
        else:
            self.fields[interface_slug] = self._get_default_field(
                interface=interface, current_value=current_value
            )

    def _get_image_field(self, *, interface, current_value):
        return self._get_default_field(
            interface=interface, current_value=current_value
        )

    def _get_file_field(self, *, interface, values, current_value):
        return self._get_default_field(
            interface=interface, current_value=current_value
        )

    def _get_default_field(self, *, interface, current_value):
        if isinstance(current_value, ComponentInterfaceValue):
            current_value = current_value.value
        return InterfaceFormField(
            instance=interface,
            initial=current_value,
            required=False,
            user=self.user,
        ).field


class SingleCIVForm(Form):
    _possible_widgets = {
        *InterfaceFormField._possible_widgets,
        autocomplete.ModelSelect2,
        Select,
    }

    def __init__(
        self, *args, pk, interface, base_obj, user, htmx_url, **kwargs
    ):
        super().__init__(*args, **kwargs)
        data = kwargs.get("data")
        qs = ComponentInterface.objects.exclude(
            slug__in=base_obj.values_for_interfaces.keys()
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
                    "data-placeholder": "Search for an interface ...",
                    "data-minimum-input-length": 3,
                    "data-theme": settings.CRISPY_TEMPLATE_PACK,
                    "data-html": True,
                }
            )
            widget_kwargs[
                "url"
            ] = "components:component-interface-autocomplete"
            interface_field_name = f"interface-{kwargs['auto_id']}"
            widget_kwargs["forward"] = [interface_field_name]
        widget_kwargs["attrs"] = attrs

        self.fields[interface_field_name] = ModelChoiceField(
            initial=selected_interface,
            queryset=qs,
            widget=widget(**widget_kwargs),
            label="Interface",
        )

        if selected_interface is not None:
            self.fields[selected_interface.slug] = InterfaceFormField(
                instance=selected_interface,
                user=user,
                required=selected_interface.value_required,
            ).field
