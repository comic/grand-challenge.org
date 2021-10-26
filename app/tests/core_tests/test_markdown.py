from django.conf import settings
from markdown import markdown

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
        TEST_MARKDOWN, extensions=settings.MARKDOWNX_MARKDOWN_EXTENSIONS,
    )

    assert output == EXPECTED_HTML
