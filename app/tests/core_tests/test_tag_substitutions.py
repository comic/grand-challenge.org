import pytest
from django.utils.safestring import SafeString, mark_safe

from grandchallenge.core.utils.tag_substitutions import TagSubstitution


@pytest.mark.parametrize(
    "tag_name,content,inp,out",
    [
        ("foo", "bar", "[ foo ]", "bar"),
        ("fo-o", "bar", "[ fo-o ]", "bar"),
        ("fo_o", "bar", "[ fo_o ]", "bar"),
        ("foo", "bar", "foo[ foo ]", "foobar"),
        ("foo", "bar", "foo[foo]", "foobar"),
        ("foo", "bar", "foo[ foo ] [foo]", "foobar bar"),
        ("foo", "bar", "[ bar ]", "[ bar ]"),
        ("foo", "bar", "foo[\nfoo\n]", "foobar"),
        ("foo", "bar", "[ foo<a> ]", "[ foo<a> ]"),
        ("foo", "<b>bar</b>", "[ foo ]", "<b>bar</b>"),
        ("foo", lambda: "bar", "[ foo ]", "bar"),
    ],
)
def test_tag_substitution(tag_name, content, inp, out):
    s = TagSubstitution(tag_name=tag_name, replacement=content)(inp)
    assert s == out


@pytest.mark.parametrize("tag_name", ["fo o", "fo\no", "'foo'", '"foo"'])
def test_no_spaces(tag_name):
    with pytest.raises(ValueError) as e:
        TagSubstitution(tag_name=tag_name, replacement="blah")
    assert "not a valid tag name" in str(e)


@pytest.mark.parametrize(
    "inp,output, repl",
    [
        ("[ foo 23aZ-_ ]", "bar23aZ-_", lambda a: f"bar{a}"),
        ("[ foo 23 ]", "bar23", lambda a: f"bar{a}"),
        ("[ foo '23' ]", "bar23", lambda a: f"bar{a}"),
        ('[ foo "23" ]', "bar23", lambda a: f"bar{a}"),
        ("[ foo 2 3 ]", "bar23", lambda a, b: f"bar{a}{b}"),
        ("[ foo 2 3 4 ]", "bar234", lambda a, b, c: f"bar{a}{b}{c}"),
    ],
)
def test_substitution_with_arguments(inp, output, repl):
    s = TagSubstitution(
        tag_name="foo",
        replacement=repl,
    )(inp)
    assert s == output


@pytest.mark.parametrize(
    "inp,content,typ",
    [
        ("[ foo ]", "<a>", str),
        (mark_safe("[ foo ]"), "<a>", str),
        ("[ foo ]", mark_safe("<a>"), str),
        (mark_safe("[ foo ]"), mark_safe("<a>"), SafeString),
        ("[ foo ]", lambda: "<a>", str),
        ("[ foo ]", lambda: mark_safe("<a>"), str),
        (mark_safe("[ foo ]"), lambda: "<a>", str),
        (mark_safe("[ foo ]"), lambda: mark_safe("<a>"), SafeString),
    ],
)
def test_safe_substitutions(inp, content, typ):
    result = TagSubstitution(tag_name="foo", replacement=content)(inp)
    assert isinstance(result, typ)


def _arg_dependent_replacement(arg):
    if arg == "unsafe":
        return "unsafe"
    else:
        return mark_safe("safe")


@pytest.mark.parametrize(
    "inp,content,typ",
    [
        ("[ foo unsafe ]", _arg_dependent_replacement, str),
        (mark_safe("[ foo unsafe ]"), _arg_dependent_replacement, str),
        ("[ foo safe ]", _arg_dependent_replacement, str),
        (mark_safe("[ foo safe ]"), _arg_dependent_replacement, SafeString),
        (mark_safe("[ foo unsafe ]"), _arg_dependent_replacement, str),
        # multiple substitutions of mixed safety
        (
            mark_safe("[ foo unsafe ] [ foo safe ]"),
            _arg_dependent_replacement,
            str,
        ),
        (
            mark_safe("[ foo safe ] [ foo safe ]"),
            _arg_dependent_replacement,
            SafeString,
        ),
    ],
)
def test_safe_substitutions_width(inp, content, typ):
    result = TagSubstitution(tag_name="foo", replacement=content)(inp)
    assert isinstance(result, typ)
