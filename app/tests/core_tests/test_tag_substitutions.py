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


@pytest.mark.parametrize(
    "inpt,typ,expected",
    [
        ("[ unsafe var-1 ]", str, "unsafe-var-1"),
        (mark_safe("[ unsafe var-1 ]"), str, "unsafe-var-1"),
        ("[ safe var-1 ]", str, "safe-var-1"),
        (mark_safe("[ safe var-1 ]"), SafeString, "safe-var-1"),
        (mark_safe("[ unsafe var-1 ]"), str, "unsafe-var-1"),
        # multiple substitutions of mixed safety
        (
            mark_safe("[ unsafe var-1 ] [ safe var-2 ]"),
            str,
            "unsafe-var-1 safe-var-2",
        ),
        (
            mark_safe("[ safe var-1 ] [ safe var-2 ]"),
            SafeString,
            "safe-var-1 safe-var-2",
        ),
    ],
)
def test_safe_substitutions_with_arguments(inpt, typ, expected):
    output = inpt

    for processor in [
        TagSubstitution(
            tag_name="safe", replacement=lambda x: mark_safe(f"safe-{x}")
        ),
        TagSubstitution(
            tag_name="unsafe", replacement=lambda x: f"unsafe-{x}"
        ),
    ]:
        output = processor(output)

    assert isinstance(output, typ)
    assert output == expected
