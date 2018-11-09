from django import forms


class JSONEditorWidget(forms.Textarea):
    template_name = "jsoneditor/jsoneditor_widget.html"

    class Media:
        css = {
            "all": (
                "https://cdnjs.cloudflare.com/ajax/libs/jsoneditor/5.25.0/jsoneditor.min.css",
            )
        }
        js = (
            "https://cdnjs.cloudflare.com/ajax/libs/jsoneditor/5.25.0/jsoneditor.min.js",
        )
