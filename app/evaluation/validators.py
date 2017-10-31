from typing import Tuple
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible


@deconstructible
class MimeTypeValidator(object):
    allowed_mimetypes = ()

    def __init__(self, *, allowed_mimetypes: Tuple[str]):
        self.allowed_mimetypes = tuple(x.lower() for x in allowed_mimetypes)
        super(MimeTypeValidator, self).__init__()

    def __call__(self, value):
        # TODO - Implement the validation
        raise ValidationError('Filetype is not valid')

    def __eq__(self, other):
        return (
            isinstance(other, MimeTypeValidator) and
            set(self.allowed_mimetypes) == set(other.allowed_mimetypes)
        )

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash(MimeTypeValidator) + 7*hash(self.allowed_mimetypes)
