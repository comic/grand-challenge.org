from django import forms
from django.template.loader import render_to_string
from markdownx.widgets import AdminMarkdownxWidget, MarkdownxWidget

from grandchallenge.core.utils.webpack import WebpackWidgetMixin


class JSONEditorWidget(WebpackWidgetMixin, forms.Textarea):
    template_name = "jsoneditor/jsoneditor_widget.html"
    webpack_bundles = ["jsoneditor_widget"]

    def __init__(self, schema=None, attrs=None):
        super().__init__(attrs)
        self.schema = schema

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context.update({"schema": self.schema})
        return context


class ColorEditorWidget(forms.TextInput):
    """
    Widget that uses the vendored jscolor for editing a color.

    Parameters
    ----------
    format
        Specify the color format by adding a format keyword:
        >>> ColorEditorWidget(format="hex")

        Options include "auto", "any", "hex", "hexa", "rgb", "rgba".
        See the jscolor (https://jscolor.com/docs/) for details.
    """

    template_name = "coloreditor/coloreditor_widget.html"

    class Media:
        js = (
            "vendored/jscolor/jscolor.min.js",
            "js/coloreditor_widget.js",
        )

    def __init__(self, attrs=None, format="auto", placeholder=None):
        super().__init__(attrs)
        self.format = format
        self.placeholder = placeholder

    def get_context(self, name, value, attrs=None):
        context = super().get_context(name, value, attrs)
        context["widget"].update(
            {
                "placeholder": self.placeholder,
                "format": self.format,
            }
        )
        return context

    def render(self, name, value, attrs=None, renderer=None):
        return render_to_string(
            self.template_name, self.get_context(name, value, attrs)
        )


class MarkdownEditorInlineWidget(MarkdownxWidget):
    template_name = "markdownx/inline_widget.html"

    @property
    def media(self):
        return forms.Media(
            js=(
                "js/markdownx.js",
                "vendored/@github/markdown-toolbar-element/dist/index.umd.js",
            )
        )


class MarkdownEditorAdminWidget(AdminMarkdownxWidget):
    template_name = "markdownx/admin_widget.html"

    @property
    def media(self):
        return forms.Media(
            css={
                "all": [
                    *AdminMarkdownxWidget.Media.css["all"],
                ]
            },
            js=[
                "js/markdownx.js",
                "vendored/@github/markdown-toolbar-element/dist/index.umd.js",
                "vendored/jquery/jquery.min.js",
                "vendored/bootstrap/js/bootstrap.bundle.min.js",
            ],
        )


class MarkdownEditorFullPageWidget(MarkdownEditorInlineWidget):
    """Customized MarkdownX widget with side-by-side panes."""

    template_name = "markdownx/full_page_widget.html"

    def __init__(self, attrs=None):
        default_attrs = {"rows": "30"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

    class Media:
        js = [
            "js/markdownx_full_page.js",
        ]
