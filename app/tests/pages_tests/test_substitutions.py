import pytest
from django.utils.safestring import SafeString, mark_safe

from grandchallenge.pages.substitutions import Substitution


@pytest.mark.parametrize(
    "tag_name,content,inp,out",
    [
        ("foo", "bar", "{% foo %}", "bar"),
        ("fo-o", "bar", "{% fo-o %}", "bar"),
        ("fo_o", "bar", "{% fo_o %}", "bar"),
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


@pytest.mark.parametrize("tag_name", ["fo o", "fo\no", "'foo'", '"foo"'])
def test_no_spaces(tag_name):
    with pytest.raises(ValueError) as e:
        Substitution(tag_name=tag_name, content="blah")
    assert "not a valid name" in str(e)


@pytest.mark.parametrize(
    "inp,content,typ",
    [
        ("{% foo %}", "<a>", str),
        (mark_safe("{% foo %}"), "<a>", str),
        ("{% foo %}", mark_safe("<a>"), str),
        (mark_safe("{% foo %}"), mark_safe("<a>"), SafeString),
    ],
)
def test_safe_substitutions(inp, content, typ):
    s = Substitution(tag_name="foo", content=content)
    assert isinstance(s.replace(inp), typ)
