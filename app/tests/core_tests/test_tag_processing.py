import pytest

from grandchallenge.core.templatetags.bleach import process_tags

EXPECTED_YOUTUBE_EMBED = """<div class="embed-responsive embed-responsive-16by9 rounded border-0">
    <iframe
            src="https://www.youtube-nocookie.com/embed/QCYYhkTlnhQ?disablekb=1&amp;rel=0"
            allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture; web-share; fullscreen"
            class="embed-responsive-item"
            loading="lazy"
            sandbox="allow-scripts allow-same-origin allow-presentation allow-popups"
    ></iframe>
</div>
"""


@pytest.mark.parametrize(
    "input_html, expected_html",
    [
        (
            "[youtube QCYYhkTlnhQ]",
            EXPECTED_YOUTUBE_EMBED,
        ),
        (  # Random white-spaces and newlines
            "[  youtube\n\t QCYYhkTlnhQ ]",
            EXPECTED_YOUTUBE_EMBED,
        ),
    ],
)
def test_youtube_tag(input_html, expected_html):
    output_html = process_tags(input_html)
    assert output_html == expected_html
