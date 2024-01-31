from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django.conf import settings
from django.forms import ModelForm

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
