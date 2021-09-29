from django.contrib import admin
from django.forms import ModelForm
from markdownx.admin import MarkdownxModelAdmin

from grandchallenge.documentation.models import DocPage


class AdminDocPageForm(ModelForm):
    class Meta:
        model = DocPage
        exclude = ()


class DocPageAdmin(MarkdownxModelAdmin):
    form = AdminDocPageForm
    list_display = (
        "pk",
        "title",
        "level",
        "order",
    )
    list_filter = ("level",)


admin.site.register(DocPage, DocPageAdmin)
