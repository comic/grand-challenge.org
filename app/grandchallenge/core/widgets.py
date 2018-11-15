import json

from django import forms


class JSONEditorWidget(forms.Textarea):
    template_name = "jsoneditor/jsoneditor_widget.html"

    def __init__(self, schema=None, attrs=None):
        super().__init__(attrs)
        self.schema = schema

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context.update({"schema": json.dumps(self.schema)})
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
