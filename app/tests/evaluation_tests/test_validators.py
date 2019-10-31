from dataclasses import dataclass

import pytest
from django.core.exceptions import ValidationError

from grandchallenge.core.validators import (
    ExtensionValidator,
    JSONSchemaValidator,
    MimeTypeValidator,
)


@dataclass
class FakeFile(object):
    name: str


def test_extension_validator():
    zip_validator = ExtensionValidator(allowed_extensions=(".zip",))
    zip_validator1 = ExtensionValidator(allowed_extensions=(".ZIP",))
    zip_and_tar_validator = ExtensionValidator(
        allowed_extensions=(".zip", ".tar")
    )
    assert zip_validator is not zip_validator1
    assert zip_validator == zip_validator1
    assert hash(zip_validator) == hash(zip_validator1)
    assert zip_validator != zip_and_tar_validator
    assert hash(zip_validator) != hash(zip_and_tar_validator)
    # Happy cases
    assert zip_validator(FakeFile("test.zip")) is None
    assert zip_validator(FakeFile("test.zIp")) is None
    assert zip_validator([FakeFile("test.zip")]) is None
    assert zip_validator([FakeFile("test.zip"), FakeFile("test1.zip")]) is None
    assert zip_and_tar_validator(FakeFile("test.zip")) is None
    assert zip_and_tar_validator(FakeFile("test.tar")) is None
    assert (
        zip_and_tar_validator([FakeFile("test.zip"), FakeFile("test.tar")])
        is None
    )
    assert zip_validator(FakeFile("test.1.zip")) is None
    with pytest.raises(ValidationError):
        zip_validator(FakeFile("test.tar"))
    with pytest.raises(ValidationError):
        zip_validator([FakeFile("test.zip"), FakeFile("test.tar")])


def test_mimetype_validator():
    json_validator = MimeTypeValidator(allowed_types=("application/json",))
    json_validator1 = MimeTypeValidator(allowed_types=("application/json",))
    text_validator = MimeTypeValidator(allowed_types=("text/plain",))
    assert json_validator is not json_validator1
    assert json_validator == json_validator1
    assert json_validator != text_validator
    assert hash(json_validator) == hash(json_validator1)
    assert hash(json_validator) != hash(text_validator)


def test_json_validator():
    schema = {
        "type": "object",
        "properties": {
            "price": {"type": "number"},
            "name": {"type": "string"},
        },
    }

    json_validator = JSONSchemaValidator(schema=schema)

    assert json_validator({"name": "Eggs", "price": 34.99}) is None
    with pytest.raises(ValidationError):
        json_validator({"name": "Eggs", "price": "invalid"})

    assert json_validator == JSONSchemaValidator(schema=schema)
    assert json_validator != JSONSchemaValidator(
        schema={"type": "object", "properties": {"name": {"type": "string"}}}
    )
    assert json_validator is not JSONSchemaValidator(schema=schema)
