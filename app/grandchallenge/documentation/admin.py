from django.contrib import admin
from django.forms import ModelForm
from markdownx.admin import MarkdownxModelAdmin

from grandchallenge.core.widgets import MarkdownEditorAdminWidget
from grandchallenge.documentation.models import DocPage


class AdminDocPageForm(ModelForm):
    class Meta:
        model = DocPage
        widgets = {
            "content": MarkdownEditorAdminWidget,
        }
        exclude = ()


class DocPageAdmin(MarkdownxModelAdmin):
    form = AdminDocPageForm
    list_display = (
        "pk",
        "title",
        "level",
    )
    list_filter = ("level",)


admin.site.register(DocPage, DocPageAdmin)
