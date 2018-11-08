
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django_select2.forms import Select2MultipleWidget

from grandchallenge.cases.models import Image
from grandchallenge.core.validators import ExtensionValidator
from grandchallenge.datasets.models import ImageSet, AnnotationSet
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


labels_upload_widget = uploader.AjaxUploadWidget(
    ajax_target_path="ajax/submission-upload/", multifile=False
)


class AnnotationSetUpdateLabelsForm(forms.ModelForm):
    chunked_upload = UploadedAjaxFileList(
        widget=labels_upload_widget,
        label="Labels File",
        validators=[ExtensionValidator(allowed_extensions=(".csv",))],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)

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
