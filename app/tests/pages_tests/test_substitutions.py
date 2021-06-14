import pytest
from django.utils.safestring import SafeString, mark_safe

from grandchallenge.pages.substitutions import Substitution
from tests.factories import PageFactory


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
    s = Substitution(tag_name=tag_name, replacement=content)
    assert s.sub(inp) == out


@pytest.mark.parametrize("tag_name", ["fo o", "fo\no", "'foo'", '"foo"'])
def test_no_spaces(tag_name):
    with pytest.raises(ValueError) as e:
        Substitution(tag_name=tag_name, replacement="blah")
    assert "not a valid tag name" in str(e)


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
    s = Substitution(tag_name="foo", replacement=content)
    assert isinstance(s.sub(inp), typ)


@pytest.mark.parametrize(
    "inp,output",
    [
        ("{% foo 23aZ-_ %}", "bar23aZ-_"),
        (mark_safe("{% foo 23 %}"), "bar23"),
        ("{% foo '23' %}", "bar23"),
        ('{% foo "23" %}', "bar23"),
    ],
)
def test_argument_substitution(inp, output):
    s = Substitution(
        tag_name="foo", replacement=mark_safe("bar{}"), use_arg=True
    )
    assert s.sub(inp) == output
    assert isinstance(s.sub(inp), type(inp))


@pytest.mark.django_db
def test_project_statistics():
    p = PageFactory(html="{% project_statistics %}")
    context = p.detail_context
    assert "participantsGeoChart" in context["cleaned_html"]
    assert context["includes_geochart"] is True
