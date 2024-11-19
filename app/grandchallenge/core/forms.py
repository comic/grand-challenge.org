import json

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms import CharField, ModelForm
from django.utils.text import format_lazy

from grandchallenge.components.models import (
    InterfaceKind,
    InterfaceKindChoices,
)
from grandchallenge.core.guardian import get_objects_for_user
from grandchallenge.core.templatetags.remove_whitespace import oxford_comma
from grandchallenge.hanging_protocols.models import ViewportNames
from grandchallenge.subdomains.utils import reverse
from grandchallenge.workstation_configs.models import WorkstationConfig
from grandchallenge.workstations.models import Workstation


class ViewContentExampleMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            interface_slugs = self.instance.interfaces.values_list(
                "slug", flat=True
            )

            if interface_slugs.count() > 0:
                self.fields[
                    "view_content"
                ].help_text += f"The following interfaces are used in your {self.instance._meta.verbose_name}: {oxford_comma(interface_slugs)}. "

            view_content_example = self.generate_view_content_example()

            if view_content_example:
                self.fields[
                    "view_content"
                ].help_text += f"Example usage: {view_content_example}. "
            else:
                self.fields[
                    "view_content"
                ].help_text += "No interfaces of type (image, chart, pdf, mp4, thumbnail_jpg, thumbnail_png) are used. At least one interface of those types is needed to config the viewer. "

        self.fields["view_content"].help_text += format_lazy(
            'Refer to the <a href="{}">documentation</a> for more information',
            reverse("documentation:detail", args=["viewer-content"]),
        )

    def generate_view_content_example(self):
        images = list(
            self.instance.interfaces.filter(kind=InterfaceKindChoices.IMAGE)
            .order_by("slug")
            .values_list("slug", flat=True)
        )
        mandatory_isolation_interfaces = list(
            self.instance.interfaces.filter(
                kind__in=InterfaceKind.interface_type_mandatory_isolation()
            )
            .order_by("slug")
            .values_list("slug", flat=True)
        )

        if not images and not mandatory_isolation_interfaces:
            return None

        overlays = list(
            self.instance.interfaces.exclude(
                kind__in=InterfaceKind.interface_type_undisplayable()
                | InterfaceKind.interface_type_mandatory_isolation()
                | {InterfaceKindChoices.IMAGE}
            )
            .order_by("slug")
            .values_list("slug", flat=True)
        )
        if images:
            overlays_per_image = len(overlays) // len(images)
            remaining_overlays = len(overlays) % len(images)

        view_content_example = {}

        for port in ViewportNames.values:
            if mandatory_isolation_interfaces:
                view_content_example[port] = [
                    mandatory_isolation_interfaces.pop(0)
                ]
            elif images:
                view_content_example[port] = [images.pop(0)]
                for _ in range(overlays_per_image):
                    view_content_example[port].append(overlays.pop(0))
                if remaining_overlays > 0:
                    view_content_example[port].append(overlays.pop(0))
                    remaining_overlays -= 1

        return json.dumps(view_content_example)


class SaveFormInitMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("save", "Save"))


class WorkstationUserFilterMixin:
    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["workstation"].queryset = get_objects_for_user(
            user,
            "workstations.view_workstation",
        ).order_by("title")
        self.fields["workstation"].initial = Workstation.objects.get(
            slug=settings.DEFAULT_WORKSTATION_SLUG
        )

        self.fields["workstation_config"].queryset = (
            WorkstationConfig.objects.order_by("title")
        )


class UserFormKwargsMixin:
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs


class PermissionRequestUpdateForm(SaveFormInitMixin, ModelForm):
    """Update form for inheritors of RequestBase"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].choices = (
            c
            for c in self.Meta.model.REGISTRATION_CHOICES
            if c[0] != self.Meta.model.PENDING
        )

    class Meta:
        fields = ("status", "rejection_text")


class UniqueTitleCreateFormMixin:
    """
    Form mixing creating an item with a unique title.

    Base class should have the `model` and `instance` attributes
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        field_order = list(self.field_order or self.fields.keys())
        self.fields["title"] = CharField(
            required=False,
            initial=self.instance and self.instance.title or "",
            max_length=self.model._meta.get_field("title").max_length,
        )
        self.order_fields(["title", *field_order])

    def clean_title(self):
        title = self.cleaned_data.get("title")
        if title and self.unique_title_query(title).exists():
            raise ValidationError(
                f"There is already an existing {self.model._meta.verbose_name} with this title"
            )
        return title

    def unique_title_query(self, title):
        return self.model.objects.filter(title=title)


class UniqueTitleUpdateFormMixin(UniqueTitleCreateFormMixin):
    def unique_title_query(self, *args, **kwargs):
        return (
            super()
            .unique_title_query(*args, **kwargs)
            .exclude(id=self.instance.pk)
        )
