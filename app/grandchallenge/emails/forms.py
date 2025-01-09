from django import forms

from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.emails.models import Email
from grandchallenge.emails.widgets import MarkdownEditorEmailFullPageWidget
from grandchallenge.subdomains.utils import reverse


class EmailMetadataForm(SaveFormInitMixin, forms.ModelForm):
    class Meta:
        model = Email
        fields = ("subject",)


class EmailBodyForm(SaveFormInitMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["body"].widget = MarkdownEditorEmailFullPageWidget(
            preview_url=reverse(
                "emails:rendered-detail", kwargs={"pk": self.instance.pk}
            )
        )

    class Meta:
        model = Email
        fields = ("body",)
