from grandchallenge.evaluation.templatetags.evaluation_extras import (
    get_jsonpath,
    user_error,
)


def test_get_jsonpath():
    obj = {"spam": {"eggs": 42, "ham": {"beans": 84}}, "chips": 21}
    # Nested lookups
    assert get_jsonpath(obj=obj, jsonpath="chips") == 21
    assert get_jsonpath(obj=obj, jsonpath="spam.ham.beans") == 84
    # The path should have precedence
    assert get_jsonpath(obj=obj, jsonpath="spam.eggs") == 42
    # Keys that don't exist
    assert get_jsonpath(obj=obj, jsonpath="foo") == ""
    assert get_jsonpath(obj=obj, jsonpath="spam.foo") == ""
    assert get_jsonpath(obj=obj, jsonpath="spam") == obj["spam"]
    assert get_jsonpath(obj=obj, jsonpath="") == ""


def test_user_error():
    assert user_error(obj="foo\n") == "foo"
    assert user_error(obj="foo") == "foo"
    assert user_error(obj="foo\n\n") == "foo"
    assert user_error(obj="foo\nbar") == "bar"
    assert user_error(obj="foo\nbar\n\n") == "bar"
    assert user_error(obj="") == ""
