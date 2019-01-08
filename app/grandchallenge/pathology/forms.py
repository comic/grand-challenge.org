from django.forms import ModelForm
from grandchallenge.pathology.models import PatientItem, StudyItem, WorklistItem
from grandchallenge.patients.models import Patient
from grandchallenge.studies.models import Study
from grandchallenge.worklists.models import Worklist

from django_select2.forms import Select2MultipleWidget
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

"""" Patient Items """


class PatientItemCreateForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("create", "Create"))

    class Meta:
        model = PatientItem
        fields = [
            "patient",
            "study",
        ]

        widgets = {
            "study": Select2MultipleWidget,
        }


class PatientItemUpdateForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("save", "Save"))

    class Meta:
        model = PatientItem
        fields = [
            "patient",
            "study",
        ]

        widgets = {
            "study": Select2MultipleWidget,
        }


""" Study Items """


class StudyItemCreateForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("create", "Create"))

    class Meta:
        model = StudyItem
        fields = [
            "study",
            "image",
        ]

        widgets = {
            "image": Select2MultipleWidget,
        }


class StudyItemUpdateForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("save", "Save"))

    class Meta:
        model = StudyItem
        fields = [
            "study",
            "image",
        ]

        widgets = {
            "image": Select2MultipleWidget,
        }


""" Worklist Items """


class WorklistItemCreateForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("create", "Create"))

    class Meta:
        model = WorklistItem
        fields = [
            "worklist",
            "image",
        ]

        widgets = {
            "image": Select2MultipleWidget,
        }


class WorklistItemUpdateForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("save", "Save"))

    class Meta:
        model = WorklistItem
        fields = [
            "worklist",
            "image",
        ]

        widgets = {
            "image": Select2MultipleWidget,
        }
