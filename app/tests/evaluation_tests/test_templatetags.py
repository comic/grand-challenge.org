from evaluation.templatetags.evaluation_extras import get_jsonpath


def test_get():
    obj = {
        'spam.eggs': 99,
        'spam': {
            'eggs': 42,
            'ham': {
                'beans': 84,
            }
        },
        'chips': 21,
    }

    # Nested lookups
    assert get_jsonpath(obj=obj, jsonpath='chips') == 21
    assert get_jsonpath(obj=obj, jsonpath='spam.ham.beans') == 84

    # The path should have precedence
    assert get_jsonpath(obj=obj, jsonpath='spam.eggs') == 42

    # Keys that don't exist
    assert get_jsonpath(obj=obj, jsonpath='foo') == ''
    assert get_jsonpath(obj=obj, jsonpath='spam.foo') == ''
    assert get_jsonpath(obj=obj, jsonpath='spam') == obj['spam']

    assert get_jsonpath(obj=obj, jsonpath='') == ''
