from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django_select2.forms import Select2MultipleWidget

from grandchallenge.cases.models import Image
from grandchallenge.core.validators import ExtensionValidator
from grandchallenge.datasets.models import AnnotationSet, ImageSet
from grandchallenge.jqfileupload.widgets import uploader
from grandchallenge.jqfileupload.widgets.uploader import UploadedAjaxFileList


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


class AnnotationSetForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("save", "Save"))

    class Meta:
        model = AnnotationSet
        fields = ("kind",)


class AnnotationSetUpdateLabelsForm(forms.ModelForm):
    chunked_upload = UploadedAjaxFileList(
        widget=uploader.AjaxUploadWidget(multifile=False),
        label="Labels File",
        validators=[ExtensionValidator(allowed_extensions=(".csv",))],
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.fields["chunked_upload"].widget.user = user

    class Meta:
        model = AnnotationSet
        fields = ("chunked_upload",)


class AnnotationSetUpdateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("save", "Save"))
        self.fields["images"].queryset = Image.objects.filter(
            origin__annotationset=self.instance
        )

    class Meta:
        model = AnnotationSet
        fields = ("images",)
        widgets = {"images": Select2MultipleWidget}
