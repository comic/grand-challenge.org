from django.forms import ModelForm
from grandchallenge.studies.models import Study

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit


class StudyCreateForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("create", "Create"))

    class Meta:
        model = Study
        fields = ["code", "region_of_interest"]


class StudyUpdateForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("save", "Save"))

    class Meta:
        model = Study
        fields = ["code", "region_of_interest"]
