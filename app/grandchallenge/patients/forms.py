from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Button, Submit
from django.forms import ModelForm

from grandchallenge.patients.models import Patient
from grandchallenge.subdomains.utils import reverse


class PatientCreateForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(
            FormActions(
                Submit("create", "Create"),
                Button(
                    "cancel",
                    "Cancel",
                    onclick=(
                        f"location.href="
                        f'"{reverse("patients:patient-display")}";'
                    ),
                ),
            )
        )

    class Meta:
        model = Patient
        fields = ["name"]


class PatientUpdateForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(
            FormActions(
                Submit("update", "Update"),
                Button(
                    "cancel",
                    "Cancel",
                    onclick=(
                        f"location.href="
                        f'"{reverse("patients:patient-display")}";'
                    ),
                ),
            )
        )

    class Meta:
        model = Patient
        fields = ["name"]
