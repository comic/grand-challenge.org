from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django.forms import ModelForm
from guardian.shortcuts import get_objects_for_user


class SaveFormInitMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("save", "Save"))


class WorkstationUserFilterMixin:
    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["workstation"].queryset = get_objects_for_user(
            user, "workstations.view_workstation", accept_global_perms=False,
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
