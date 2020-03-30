from django.contrib import admin
from django.forms import ModelForm
from markdownx.admin import MarkdownxModelAdmin

from grandchallenge.core.widgets import MarkdownEditorAdminWidget
from grandchallenge.overview_pages.models import OverviewPage


class OverviewPageForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in [
            "algorithms",
            "archives",
            "challenges",
            "reader_studies",
        ]:
            self.fields[field].widget.can_add_related = False

    class Meta:
        model = OverviewPage
        widgets = {
            "detail_page_markdown": MarkdownEditorAdminWidget,
        }
        exclude = ("description",)


class OverviewPageAdmin(MarkdownxModelAdmin):
    form = OverviewPageForm


admin.site.register(OverviewPage, OverviewPageAdmin)
