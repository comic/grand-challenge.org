import pytest
from django.conf import settings
from markdown import markdown

from grandchallenge.core.utils.markdown import EmbedYoutubeExtension

TEST_MARKDOWN = """
![](whatever.png)

> Quote Me

Markdown | Less | Pretty
--- | --- | ---
*Still* | `renders` | **nicely**
1 | 2 | 3

```python
 def test_function():
    pass
```
"""

EXPECTED_HTML = """<p><img alt="" class="img-fluid" src="whatever.png" /></p>
<blockquote class="blockquote">
<p>Quote Me</p>
</blockquote>
<table class="table table-hover table-borderless">
<thead class="thead-light">
<tr>
<th>Markdown</th>
<th>Less</th>
<th>Pretty</th>
</tr>
</thead>
<tbody>
<tr>
<td><em>Still</em></td>
<td><code class="codehilite">renders</code></td>
<td><strong>nicely</strong></td>
</tr>
<tr>
<td>1</td>
<td>2</td>
<td>3</td>
</tr>
</tbody>
</table>
<div class="codehilite"><pre><span></span><code> <span class="k">def</span> <span class="nf">test_function</span><span class="p">():</span>
    <span class="k">pass</span>
</code></pre></div>"""


def test_markdown_rendering():
    output = markdown(
        TEST_MARKDOWN, extensions=settings.MARKDOWNX_MARKDOWN_EXTENSIONS
    )

    assert output == EXPECTED_HTML


def _gen_expected_iframe(width=480, height=270):
    return (
        "<p>\n"
        '<iframe allow="accelerometer; autoplay; encrypted-media; gyroscope; '
        'picture-in-picture; web-share; fullscreen" allowfullscreen="" '
        f'class="youtube embedded-responsive" frameborder="0" height="{height!r}" '
        'src="https://www.youtube-nocookie.com/embed/QCYYhkTlnhQ?disablekb=1&amp;rel=0&amp;" '
        f'width="{width!r}"><a href="https://www.youtube.com/watch?v=QCYYhkTlnhQ" '
        'target="_blank">View YouTube video</a></iframe>\n'
        "</p>"
    )


@pytest.mark.parametrize(
    "md, expected_html",
    [
        (
            "[youtube QCYYhkTlnhQ]",
            _gen_expected_iframe(),
        ),
        (  # Random white-spaces and newlines
            "[  youtube\n\t QCYYhkTlnhQ ]",
            _gen_expected_iframe(),
        ),
        (  # add width
            "[youtube QCYYhkTlnhQ 600]",
            _gen_expected_iframe(width=600),
        ),
        (  # add width and height
            "[youtube QCYYhkTlnhQ 600 500]",
            _gen_expected_iframe(width=600, height=500),
        ),
        (  # minim width and height
            "[youtube QCYYhkTlnhQ 1 1]",
            _gen_expected_iframe(),
        ),
    ],
)
def test_youtube_embed(md, expected_html):
    output_html = markdown(md, extensions=[EmbedYoutubeExtension()])

    assert output_html == expected_html
