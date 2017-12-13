import pytest
from django.core.exceptions import ValidationError

from evaluation.validators import ExtensionValidator

class FakeFile(object):
    def __init__(self, name):
        self.name = name

def test_extension_validator():
    zip_validator = ExtensionValidator(allowed_extensions=('.zip',))
    zip_validator1 = ExtensionValidator(allowed_extensions=('.ZIP',))
    zip_and_tar_validator = ExtensionValidator(allowed_extensions=('.zip', '.tar'))

    assert zip_validator is not zip_validator1
    assert zip_validator == zip_validator1
    assert hash(zip_validator) == hash(zip_validator1)
    assert zip_validator != zip_and_tar_validator
    assert hash(zip_validator) != hash(zip_and_tar_validator)

    # Happy cases
    assert zip_validator(FakeFile('test.zip')) is None
    assert zip_validator(FakeFile('test.zIp')) is None
    assert zip_validator([FakeFile('test.zip')])
    assert zip_validator([FakeFile('test.zip'), FakeFile('test1.zip')]) is None
    assert zip_and_tar_validator(FakeFile('test.zip')) is None
    assert zip_and_tar_validator(FakeFile('test.tar')) is None
    assert zip_and_tar_validator([FakeFile('test.zip'), FakeFile('test.tar')]) is None

    with pytest.raises(ValidationError):
        zip_validator(FakeFile('test.tar'))

    with pytest.raises(ValidationError):
        zip_validator([FakeFile('test.zip'), FakeFile('test.tar')])
