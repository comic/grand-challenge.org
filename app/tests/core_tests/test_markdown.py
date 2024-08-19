import pytest
from django.conf import settings
from markdown import markdown

from grandchallenge.core.utils.markdown import BS4Treeprocessor

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


@pytest.mark.parametrize(
    "markdown_with_html, expected_output",
    (
        (
            """<img src="https://rumc-gcorg-p-public.s3.amazonaws.com/i/2023/10/20/042179f0-ad8c-4c0b-af54-7e81ba389a90.jpeg"/>
         [![](http://minio.localhost:9000/grand-challenge-public/i/2024/08/06/77c8d999-c22b-4983-8558-8e1fa364cd2c.jpg)](https://google.com)""",
            """<p><img class="img-fluid" src="https://rumc-gcorg-p-public.s3.amazonaws.com/i/2023/10/20/042179f0-ad8c-4c0b-af54-7e81ba389a90.jpeg"/>
         <a href="https://google.com"><img alt="" class="img-fluid" src="http://minio.localhost:9000/grand-challenge-public/i/2024/08/06/77c8d999-c22b-4983-8558-8e1fa364cd2c.jpg" /></a></p>""",
        ),
        (
            """<img class="" src="https://rumc-gcorg-p-public.s3.amazonaws.com/i/2023/10/20/042179f0-ad8c-4c0b-af54-7e81ba389a90.jpeg"/>
         [![](http://minio.localhost:9000/grand-challenge-public/i/2024/08/06/77c8d999-c22b-4983-8558-8e1fa364cd2c.jpg)](https://google.com)""",
            """<p><img class="img-fluid" src="https://rumc-gcorg-p-public.s3.amazonaws.com/i/2023/10/20/042179f0-ad8c-4c0b-af54-7e81ba389a90.jpeg"/>
         <a href="https://google.com"><img alt="" class="img-fluid" src="http://minio.localhost:9000/grand-challenge-public/i/2024/08/06/77c8d999-c22b-4983-8558-8e1fa364cd2c.jpg" /></a></p>""",
        ),
        (
            """<img class="ml-2" src="https://rumc-gcorg-p-public.s3.amazonaws.com/i/2023/10/20/042179f0-ad8c-4c0b-af54-7e81ba389a90.jpeg"/>
         [![](http://minio.localhost:9000/grand-challenge-public/i/2024/08/06/77c8d999-c22b-4983-8558-8e1fa364cd2c.jpg)](https://google.com)""",
            """<p><img class="ml-2 img-fluid" src="https://rumc-gcorg-p-public.s3.amazonaws.com/i/2023/10/20/042179f0-ad8c-4c0b-af54-7e81ba389a90.jpeg"/>
         <a href="https://google.com"><img alt="" class="img-fluid" src="http://minio.localhost:9000/grand-challenge-public/i/2024/08/06/77c8d999-c22b-4983-8558-8e1fa364cd2c.jpg" /></a></p>""",
        ),
        (
            """<img class="img-fluid" src="https://rumc-gcorg-p-public.s3.amazonaws.com/i/2023/10/20/042179f0-ad8c-4c0b-af54-7e81ba389a90.jpeg"/>
         [![](http://minio.localhost:9000/grand-challenge-public/i/2024/08/06/77c8d999-c22b-4983-8558-8e1fa364cd2c.jpg)](https://google.com)""",
            """<p><img class="img-fluid" src="https://rumc-gcorg-p-public.s3.amazonaws.com/i/2023/10/20/042179f0-ad8c-4c0b-af54-7e81ba389a90.jpeg"/>
         <a href="https://google.com"><img alt="" class="img-fluid" src="http://minio.localhost:9000/grand-challenge-public/i/2024/08/06/77c8d999-c22b-4983-8558-8e1fa364cd2c.jpg" /></a></p>""",
        ),
        (
            """<img class="ml-2 img-fluid" src="https://rumc-gcorg-p-public.s3.amazonaws.com/i/2023/10/20/042179f0-ad8c-4c0b-af54-7e81ba389a90.jpeg"/>
         [![](http://minio.localhost:9000/grand-challenge-public/i/2024/08/06/77c8d999-c22b-4983-8558-8e1fa364cd2c.jpg)](https://google.com)""",
            """<p><img class="ml-2 img-fluid" src="https://rumc-gcorg-p-public.s3.amazonaws.com/i/2023/10/20/042179f0-ad8c-4c0b-af54-7e81ba389a90.jpeg"/>
         <a href="https://google.com"><img alt="" class="img-fluid" src="http://minio.localhost:9000/grand-challenge-public/i/2024/08/06/77c8d999-c22b-4983-8558-8e1fa364cd2c.jpg" /></a></p>""",
        ),
    ),
)
def test_setting_class_to_html_img_within_markdown(
    markdown_with_html, expected_output
):

    output = markdown(
        text=markdown_with_html or "",
        extensions=settings.MARKDOWNX_MARKDOWN_EXTENSIONS,
        extension_configs=settings.MARKDOWNX_MARKDOWN_EXTENSION_CONFIGS,
    )

    assert output == expected_output


def test_tree_processor_set_css_class_type_error():
    with pytest.raises(TypeError):
        BS4Treeprocessor.set_css_class("element", "img-fluid")
