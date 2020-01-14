import pytest

from grandchallenge.pages.substitutions import Substitution


@pytest.mark.parametrize(
    "tag_name,content,inp,out",
    [
        ("foo", "bar", "{% foo %}", "bar"),
        ("foo", "bar", "foo{% foo %}", "foobar"),
        ("foo", "bar", "foo{%foo%}", "foobar"),
        ("foo", "bar", "foo{% foo %} {%foo%}", "foobar bar"),
        ("foo", "bar", "{% bar %}", "{% bar %}"),
        ("foo", "bar", "foo{%\nfoo\n%}", "foobar"),
        ("foo", "bar", "{% foo<a> %}", "{% foo<a> %}"),
        ("foo", "<b>bar</b>", "{% foo %}", "<b>bar</b>"),
    ],
)
def test_substitution(tag_name, content, inp, out):
    s = Substitution(tag_name=tag_name, content=content)
    assert s.replace(inp) == out
