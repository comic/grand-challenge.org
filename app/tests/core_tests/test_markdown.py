import textwrap

import pytest
from django.utils.safestring import SafeString, mark_safe

from grandchallenge.core.templatetags.bleach import md2html
from grandchallenge.core.utils.markdown import ExtendHTMLTagClasses


@pytest.mark.parametrize(
    "markdown_with_html, expected_output",
    (
        (
            textwrap.dedent(
                """
                ![](test.png)

                > Quote Me

                Markdown | Less | Pretty
                --- | --- | ---
                *Still* | `renders` | **nicely**
                1 | 2 | 3

                ```python
                def test_function():
                    pass
                ```"""
            ),
            textwrap.dedent(
                """\
                <p><img class="img-fluid" src="test.png"/></p>
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
                <div class="codehilite"><pre><span></span><span class="k">def</span> <span class="nf">test_function</span><span class="p">():</span>
                    <span class="k">pass</span>
                </pre></div>"""
            ),
        ),
        (
            textwrap.dedent(
                r"""
                ![](test.png)

                <img src="test-no-class.png"/>

                <img class="" src="test-empty-class.png"/>

                <img class="ml-3"src="test-existing-class.png"/>

                > Quote Me

                <blockquote>
                <p>Quote Me No Class</p>
                </blockquote>
                <blockquote class="ml-3">
                <p>Quote Me Existing Class</p>
                </blockquote>

                Markdown | Less | Pretty
                --- | --- | ---
                *Still* | `renders` | **nicely**
                1 | 2 | 3

                <table>
                <thead>
                <tr>
                <th>no class</th>
                </tr>
                </thead>
                <tbody>
                </tbody>
                </table>

                <table class="ml-3">
                <thead class="ml-3">
                <tr>
                <th>existing class</th>
                </tr>
                </thead>
                <tbody>
                </tbody>
                </table>

                ```python
                def test_function():
                    pass
                ```
                <div><pre><code>no class</code></pre></div>
                <div class="ml-3"><pre><code class="ml-3">existing class</code></pre></div>

                ~~Delete me~~

                CH~3~CH~2~OH
                text~a\ subscript~

                - Just paste links directly in the document like this: https://google.com.
                - Or even an email address: fake.email@email.com.
                """
            ),
            textwrap.dedent(
                """\
                <p><img class="img-fluid" src="test.png"/></p>
                <p><img class="img-fluid" src="test-no-class.png"/></p>
                <p><img class="img-fluid" src="test-empty-class.png"/></p>
                <p><img class="ml-3 img-fluid" src="test-existing-class.png"/></p>
                <blockquote class="blockquote">
                <p>Quote Me</p>
                </blockquote>
                <blockquote class="blockquote">
                <p>Quote Me No Class</p>
                </blockquote>
                <blockquote class="ml-3 blockquote">
                <p>Quote Me Existing Class</p>
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
                <table class="table table-hover table-borderless">
                <thead class="thead-light">
                <tr>
                <th>no class</th>
                </tr>
                </thead>
                <tbody>
                </tbody>
                </table>
                <table class="ml-3 table table-hover table-borderless">
                <thead class="ml-3 thead-light">
                <tr>
                <th>existing class</th>
                </tr>
                </thead>
                <tbody>
                </tbody>
                </table>
                <div class="codehilite"><pre><span></span><span class="k">def</span> <span class="nf">test_function</span><span class="p">():</span>
                    <span class="k">pass</span>
                </pre></div>
                <div><pre><code class="codehilite">no class</code></pre></div>
                <div class="ml-3"><pre><code class="ml-3 codehilite">existing class</code></pre></div>
                <p><del>Delete me</del></p>
                <p>CH<sub>3</sub>CH<sub>2</sub>OH
                text<sub>a subscript</sub></p>
                <ul>
                <li>Just paste links directly in the document like this: <a href="https://google.com">https://google.com</a>.</li>
                <li>Or even an email address: <a href="&#109;&#97;&#105;&#108;&#116;&#111;&#58;&#102;&#97;&#107;&#101;&#46;&#101;&#109;&#97;&#105;&#108;&#64;&#101;&#109;&#97;&#105;&#108;&#46;&#99;&#111;&#109;">&#102;&#97;&#107;&#101;&#46;&#101;&#109;&#97;&#105;&#108;&#64;&#101;&#109;&#97;&#105;&#108;&#46;&#99;&#111;&#109;</a>.</li>
                </ul>"""
            ),
        ),
        (
            "&lt;script&gt;alert(&quot;foo&quot;)&lt;/script&gt;",
            "<p>&lt;script&gt;alert(&quot;foo&quot;)&lt;/script&gt;</p>",
        ),
        (
            "[![](http://minio.localhost:9000/grand-challenge-public/i/2024/08/06/77c8d999-c22b-4983-8558-8e1fa364cd2c.jpg)](https://google.com)",
            '<p><a href="https://google.com"><img class="img-fluid" src="http://minio.localhost:9000/grand-challenge-public/i/2024/08/06/77c8d999-c22b-4983-8558-8e1fa364cd2c.jpg"/></a></p>',
        ),
    ),
)
def test_markdown_rendering(markdown_with_html, expected_output):
    output = md2html(markdown=markdown_with_html)
    assert output == expected_output


@pytest.mark.parametrize(
    "html, tag_classes, expected_output, is_safe",
    [
        (  # Safe input
            mark_safe("<div>Content</div>"),
            {},
            "<div>Content</div>",
            True,
        ),
        (  # Unsafe input
            "<div>Content</div>",
            {},
            "<div>Content</div>",
            False,
        ),
        (  # Escaped classes
            mark_safe("<div>Content</div>"),
            {"div": ['<script>alert("foo")</script>']},
            '<div class="&lt;script&gt;alert(&quot;foo&quot;)&lt;/script&gt;">Content</div>',
            True,
        ),
        (  # Empty class
            '<div class="">Content</div>',
            {"div": ["foo"]},
            '<div class="foo">Content</div>',
            False,
        ),
        (  # Existing class
            '<div class="ml-2">Content</div>',
            {"div": ["foo"]},
            '<div class="ml-2 foo">Content</div>',
            False,
        ),
        (  # Extension class already present
            '<div class="foo">Content</div>',
            {"div": ["foo"]},
            '<div class="foo">Content</div>',
            False,
        ),
        (  # Existing class + extension class
            '<div class="ml-2 foo">Content</div>',
            {"div": ["foo"]},
            '<div class="ml-2 foo">Content</div>',
            False,
        ),
    ],
)
def test_extend_html_tag_classes(html, tag_classes, expected_output, is_safe):
    extender = ExtendHTMLTagClasses(tag_classes)
    output = extender(html)

    assert output == expected_output

    # Check if the output matches the expected safety status
    assert isinstance(output, SafeString) == is_safe
