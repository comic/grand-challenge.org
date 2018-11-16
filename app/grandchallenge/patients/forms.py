from django.forms import ModelForm
from grandchallenge.patients.models import Patient

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit


class PatientDetailForm(ModelForm):
    class Meta:
        model = Patient
        fields = ("name", "sex", "height")


class PatientCreateForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("create", "Create"))

    class Meta:
        model = Patient
        fields = [
            "name",
            "sex",
            "height",
        ]


class PatientUpdateForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("save", "Save"))

    class Meta:
        model = Patient
        fields = [
            "id",
            "name",
            "sex",
            "height",
        ]
