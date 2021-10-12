from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django.contrib.flatpages.forms import FlatpageForm
from django.contrib.flatpages.models import FlatPage
from django.contrib.sites.models import Site


from grandchallenge.core.widgets import MarkdownEditorWidget


class FlatPageForm(FlatpageForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            self.fields["url"].initial = self.instance.url
        self.fields["sites"].initial = Site.objects.get_current()
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("save", "Save"))

    class Meta:
        model = FlatPage
        fields = (
            "title",
            "content",
            "registration_required",
            "url",
            "sites",
        )
        widgets = {
            "content": MarkdownEditorWidget,
        }
