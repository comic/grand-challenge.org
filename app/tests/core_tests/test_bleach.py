import pytest

from grandchallenge.core.templatetags.bleach import clean


@pytest.mark.parametrize(
    "html, expected_cleaned, kwargs",
    [
        # Default kicks out variants they are not allowed
        ["<iframe />", "", {}],
        ["<iframe></iframe>", "", {}],
        ["<iframe><iframe></iframe></iframe>", "", {}],
        ["<iframe>", "", {}],
        # Allowing limits to specific sources
        ["<iframe></iframe>", "<iframe></iframe>", {"allow_iframes": True}],
        [
            (
                html := '<iframe src="https://www.youtube-nocookie.com/embed/QCYYhkTlnhQ"></iframe>'
            ),
            html,
            {"allow_iframes": True},
        ],
        # Not allowed src is stripped
        [
            "<iframe src='not-youtube.com'></iframe>",
            "<iframe></iframe>",
            {"allow_iframes": True},
        ],
        # Attributes are allowed
        [
            (
                html := '<iframe src="https://www.youtube-nocookie.com/embed/QCYYhkTlnhQ" class="youtube" allow="fullscreen" sandbox=""></iframe>'
            ),
            html,
            {"allow_iframes": True},
        ],
        [  # Tricky sources
            "<iframe src='https://www.youtube-nocookie.com.evilcorp.com/embed/QCYYhkTlnhQ'></iframe>",
            "<iframe></iframe>",
            {"allow_iframes": True},
        ],
    ],
)
def test_iframes_bleaching(html, expected_cleaned, kwargs):
    cleaned = clean(html, **kwargs)
    assert cleaned == expected_cleaned
