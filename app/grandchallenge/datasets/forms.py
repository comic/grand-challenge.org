# -*- coding: utf-8 -*-

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django_select2.forms import Select2MultipleWidget

from grandchallenge.cases.models import Image
from grandchallenge.datasets.models import ImageSet


class ImageSetCreateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("save", "Save"))

    class Meta:
        model = ImageSet
        fields = ("phase",)


class ImageSetUpdateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("save", "Save"))

        self.fields["images"].queryset = Image.objects.filter(
            origin__imageset=self.instance
        )

    class Meta:
        model = ImageSet
        fields = ("images",)
        widgets = {"images": Select2MultipleWidget}
