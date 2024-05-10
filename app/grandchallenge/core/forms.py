from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms import CharField, ModelForm

from grandchallenge.core.guardian import get_objects_for_user
from grandchallenge.workstation_configs.models import WorkstationConfig
from grandchallenge.workstations.models import Workstation


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


class CreateTitleFormMixin:
    model = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["title"] = CharField(
            required=False,
            initial=self.instance and self.instance.title or "",
            max_length=self.model._meta.get_field("title").max_length,
        )

    class Meta:
        non_civ_fields = ("title",)

    def clean_title(self):
        title = self.cleaned_data.get("title")
        if title and self._unique_title_query(title).exists():
            raise ValidationError(
                f"An {self.model._meta.verbose_name} already exists with this title"
            )
        return title

    def _unique_title_query(self, title):
        return self.model.objects.filter(
            title=title,
        )


class UpdateTitleFormMixin(CreateTitleFormMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.is_editable:
            for _, field in self.fields.items():
                field.disabled = True

    def _unique_title_query(self, *args, **kwargs):
        return (
            super()
            ._unique_title_query(*args, **kwargs)
            .exclude(id=self.instance.pk)
        )
