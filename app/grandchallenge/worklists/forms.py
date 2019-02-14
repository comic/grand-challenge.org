from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django.forms import ModelForm
from django_select2.forms import Select2MultipleWidget

from grandchallenge.cases.models import Image, ImageFile
from grandchallenge.worklists.models import Worklist, WorklistSet


""" Worklist """


class WorklistCreateForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("create", "Create"))
        self.fields["images"].queryset = Image.objects.filter(
            study__isnull=False, files__image_type=ImageFile.IMAGE_TYPE_TIFF
        )

    class Meta:
        model = Worklist
        fields = ["title", "set", "images"]
        widgets = {"images": Select2MultipleWidget}


class WorklistUpdateForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("save", "Save"))
        self.fields["images"].queryset = Image.objects.filter(
            study__isnull=False, files__image_type=ImageFile.IMAGE_TYPE_TIFF
        )

    class Meta:
        model = Worklist
        fields = ["title", "set", "images"]
        widgets = {"images": Select2MultipleWidget}


""" WorklistSet """


class WorklistSetCreateForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("create", "Create"))

    class Meta:
        model = WorklistSet
        fields = ["title", "user"]


class WorklistSetUpdateForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("save", "Save"))
        self.helper.layout.append()

    class Meta:
        model = WorklistSet
        fields = ["title", "user"]
