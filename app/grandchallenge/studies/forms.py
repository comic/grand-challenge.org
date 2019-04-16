from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Button, Submit
from django.forms import ModelForm, DateTimeInput

from grandchallenge.studies.models import Study
from grandchallenge.subdomains.utils import reverse


class StudyForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(
            FormActions(
                Submit("save", "Save"),
                Button(
                    "cancel",
                    "Cancel",
                    onclick=(
                        f"location.href=" f'"{reverse("patients:list")}";'
                    ),
                ),
            )
        )

    class Meta:
        model = Study
        fields = ["name", "datetime", "patient"]
        widgets = {"datetime": DateTimeInput(format="%d-%m-%Y %H%M",attrs={"type": "datetime"})}
