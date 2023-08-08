import json

import pytest
import referencing

from grandchallenge.core.validators import JSONSchemaRegistry


@pytest.mark.parametrize(
    "first,second",
    (
        ([], []),
        (["a"], ["a"]),
        (["a"], ["a", "a"]),
        (["a", "b", "c"], ["c", "b", "a"]),
    ),
)
def test_singletons(first, second):
    registry = JSONSchemaRegistry(allowed_regexes=first)
    other_registry = JSONSchemaRegistry(allowed_regexes=second)
    assert registry is other_registry


def test_disallowed():
    registry = JSONSchemaRegistry(allowed_regexes=["https://an_unrelated_ref"])
    with pytest.raises(referencing.exceptions.NoSuchResource):
        registry.get_or_retrieve("https://a_disallowed_ref")


def test_allowed(mocker):
    ref = "https://an_allowed_ref"
    registry = JSONSchemaRegistry(allowed_regexes=[ref])

    # Setup mock response
    ref_content = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "number",
    }

    mock_reponse = mocker.Mock()
    mock_reponse.text = json.dumps(ref_content)
    mocker.patch(
        "grandchallenge.core.validators.requests.get",
        return_value=mock_reponse,
    )

    assert registry.get_or_retrieve(ref).value.contents == ref_content
