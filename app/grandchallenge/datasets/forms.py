# -*- coding: utf-8 -*-
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms

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

    class Meta:
        model = ImageSet
        fields = ("images",)
