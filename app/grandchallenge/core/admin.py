from django.contrib import admin
from django.contrib.flatpages.admin import FlatPageAdmin
from django.contrib.flatpages.forms import FlatpageForm
from django.contrib.flatpages.models import FlatPage

from grandchallenge.core.widgets import MarkdownEditorAdminWidget


class MarkdownFlatPageForm(FlatpageForm):
    class Meta(FlatpageForm.Meta):
        widgets = {"content": MarkdownEditorAdminWidget()}


class MarkdownFlatPageAdmin(FlatPageAdmin):
    form = MarkdownFlatPageForm


admin.site.unregister(FlatPage)
admin.site.register(FlatPage, MarkdownFlatPageAdmin)
