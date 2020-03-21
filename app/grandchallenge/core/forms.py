from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from guardian.shortcuts import get_objects_for_user

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
            f"{Workstation._meta.app_label}.view_{Workstation._meta.model_name}",
            Workstation,
        )
