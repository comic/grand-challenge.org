from django.contrib import admin
from django.forms import ModelForm
from markdownx.admin import MarkdownxModelAdmin

from grandchallenge.documentation.models import DocPage


class AdminDocPageForm(ModelForm):
    class Meta:
        model = DocPage
        fields = (
            "title",
            "content",
            "parent",
        )
        ordering = ("order",)


class DocPageAdmin(MarkdownxModelAdmin):
    form = AdminDocPageForm
    list_display = (
        "pk",
        "title",
        "order",
    )


admin.site.register(DocPage, DocPageAdmin)
