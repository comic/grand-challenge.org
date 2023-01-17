from django import forms
from django.template.loader import render_to_string
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
        css = {"all": ("vendored/jsoneditor/jsoneditor.min.css",)}
        js = ("vendored/jsoneditor/jsoneditor.min.js",)


class ColorEditorWidget(forms.TextInput):
    """
    Widget that uses the vendored jscolor for editing a color.

    Specify the color format by adding a format keyword:
    >>> ColorEditorWidget(format="hex")

    See the jscolor documentation for more

    """

    template_name = "coloreditor/coloreditor_widget.html"

    class Media:
        js = (
            "vendored/jscolor/jscolor.min.js",
            "js/coloreditor_widget.js",
        )

    def __init__(self, attrs=None, format="auto"):
        self.format = format
        super().__init__(attrs)

    def get_context(self, name, value, attrs=None):
        context = {}
        context.update(self.attrs.copy() or {})
        context.update(attrs or {})
        context.update(
            {
                "widget": self,
                "name": name,
                "value": value,
            }
        )
        return context

    def render(self, name, value, attrs=None, renderer=None):
        return render_to_string(
            self.template_name, self.get_context(name, value, attrs)
        )


class MarkdownEditorWidget(MarkdownxWidget):
    @property
    def media(self):
        return forms.Media(
            js=(
                "js/markdownx.js",
                "vendor/js/markdown-toolbar-element/index.umd.js",
            )
        )


class MarkdownEditorAdminWidget(AdminMarkdownxWidget):
    @property
    def media(self):
        return forms.Media(
            css={
                "all": [
                    *AdminMarkdownxWidget.Media.css["all"],
                    "vendor/css/base.min.css",
                    "vendor/fa/css/all.css",
                    "css/markdown.css",
                ]
            },
            js=[
                "js/markdownx.js",
                "vendor/js/markdown-toolbar-element/index.umd.js",
                "vendor/js/jquery.min.js",
                "vendor/js/bootstrap.bundle.min.js",
            ],
        )
