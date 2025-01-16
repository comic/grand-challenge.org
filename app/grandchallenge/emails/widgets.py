from grandchallenge.core.widgets import MarkdownEditorFullPageWidget


class MarkdownEditorEmailFullPageWidget(MarkdownEditorFullPageWidget):
    template_name = "emails/email_full_page_markdown_widget.html"

    def __init__(self, *args, preview_url, **kwargs):
        super().__init__(*args, **kwargs)
        self.preview_url = preview_url

    def add_markdownx_attrs(self, *args, **kwargs):
        attrs = super().add_markdownx_attrs(*args, **kwargs)
        attrs.update(
            {
                "data-markdownx-urls-path": self.preview_url,
            }
        )
        return attrs

    class Media:
        js = [
            "js/emails/email_markdown_preview.mjs",
        ]
