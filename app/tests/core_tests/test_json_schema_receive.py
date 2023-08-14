import json

import pytest
import referencing

from grandchallenge.core.validators import JSONSchemaRetrieve


def test_disallowed():
    registry = referencing.Registry(
        retrieve=JSONSchemaRetrieve(
            allowed_regexes=["https://an_unrelated_ref"]
        )
    )
    with pytest.raises(referencing.exceptions.NoSuchResource):
        registry.get_or_retrieve("https://a_disallowed_ref")


def test_json_schema_receive(mocker):
    ref = "https://an_allowed_ref"
    registry = referencing.Registry(
        retrieve=JSONSchemaRetrieve(allowed_regexes=[ref])
    )

    # Setup mock response
    ref_content = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "number",
    }

    mock_response = mocker.Mock()
    mock_response.text = json.dumps(ref_content)
    mock_request_get = mocker.patch(
        "grandchallenge.core.validators.requests.get",
        return_value=mock_response,
    )

    for _ in [1, 2]:
        assert registry.get_or_retrieve(ref).value.contents == ref_content

    # Calling same registry twice hits the cache
    mock_request_get.assert_called_once()

    # A new registry still hits the cache
    new_registry = referencing.Registry(
        retrieve=JSONSchemaRetrieve(allowed_regexes=[ref])
    )
    assert new_registry.get_or_retrieve(ref).value.contents == ref_content

    mock_request_get.assert_called_once()
