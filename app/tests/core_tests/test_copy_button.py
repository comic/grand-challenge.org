from grandchallenge.core.templatetags.copy_button import (
    copy_button,
    copy_button_only,
)


class TestCopyButtonOnly:
    def test_renders_button_with_value(self):
        result = copy_button_only(value="test-value")
        assert 'data-copy="test-value"' in result

    def test_default_title(self):
        result = copy_button_only(value="x")
        assert 'title="Copy to clipboard"' in result

    def test_custom_title(self):
        result = copy_button_only(value="x", title="Custom title")
        assert 'title="Custom title"' in result

    def test_escapes_html_in_value(self):
        result = copy_button_only(value='<script>alert("xss")</script>')
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_escapes_html_in_title(self):
        result = copy_button_only(value="x", title='<img src="x">')
        assert "<img" not in result


class TestCopyButton:
    def test_contains_copy_button(self):
        result = copy_button("abc-def-ghi")
        assert 'data-copy="abc-def-ghi"' in result

    def test_display_value_is_prefix_before_first_dash(self):
        result = copy_button("abc-def-ghi")
        assert "abc" in result

    def test_no_link_by_default(self):
        result = copy_button("abc-def")
        assert "<a" not in result

    def test_with_link(self):
        result = copy_button("abc-def", "/some/url/")
        assert 'href="/some/url/"' in result
