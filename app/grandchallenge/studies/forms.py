from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Button, Submit
from django.forms import ModelForm, DateTimeInput

from grandchallenge.subdomains.utils import reverse
from grandchallenge.studies.models import Study


class StudyCreateForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(
            FormActions(
                Submit("create", "Create"),
                Button(
                    "cancel",
                    "Cancel",
                    onclick="location.href='%s';"
                    % reverse("studies:study-display"),
                ),
            )
        )

    class Meta:
        model = Study
        fields = ["name", "datetime", "patient"]
        widgets = {"datetime": DateTimeInput(format="%d/%m/%Y %H:%M:%S")}


class StudyUpdateForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(
            FormActions(
                Submit("create", "Create"),
                Button(
                    "cancel",
                    "Cancel",
                    onclick="location.href='%s';"
                    % reverse("studies:study-display"),
                ),
            )
        )

    class Meta:
        model = Study
        fields = ["name", "datetime", "patient"]
        widgets = {"datetime": DateTimeInput(format="%d/%m/%Y %H:%M:%S")}
