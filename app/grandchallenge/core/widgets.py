from django import forms
from markdownx.widgets import AdminMarkdownxWidget, MarkdownxWidget


class JSONEditorWidget(forms.Textarea):
    template_name = "jsoneditor/jsoneditor_widget.html"

    def __init__(self, schema=None, attrs=None):
        super().__init__(attrs)
        self.schema = schema

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context.update({"schema": self.schema})
        return context

    class Media:
        css = {
            "all": (
                "https://cdnjs.cloudflare.com/ajax/libs/jsoneditor/5.25.0/jsoneditor.min.css",
            )
        }
        js = (
            "https://cdnjs.cloudflare.com/ajax/libs/jsoneditor/5.25.0/jsoneditor.min.js",
        )


class MarkdownEditorWidget(MarkdownxWidget):
    class Media(MarkdownxWidget.Media):
        js = [
            *MarkdownxWidget.Media.js,
            "vendor/js/markdown-toolbar-element/index.umd.js",
        ]


class MarkdownEditorAdminWidget(AdminMarkdownxWidget):
    class Media(AdminMarkdownxWidget.Media):
        css = {
            "all": [
                *AdminMarkdownxWidget.Media.css["all"],
                "vendor/css/base.min.css",
                "vendor/fa/css/all.css",
            ]
        }
        js = [
            *AdminMarkdownxWidget.Media.js,
            "vendor/js/markdown-toolbar-element/index.umd.js",
        ]
