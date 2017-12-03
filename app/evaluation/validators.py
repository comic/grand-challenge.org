import io
import json
import tarfile
from typing import Tuple

import magic
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible


@deconstructible
class MimeTypeValidator(object):
    allowed_types = ()

    def __init__(self, *, allowed_types: Tuple[str, ...]):
        self.allowed_types = tuple(x.lower() for x in allowed_types)
        super(MimeTypeValidator, self).__init__()

    def __call__(self, value):
        mimetype = magic.from_buffer(value.read(), mime=True)

        if mimetype.lower() not in self.allowed_types:
            raise ValidationError(f'File of type {mimetype} is not supported. '
                                  'Allowed types are '
                                  f'{", ".join(self.allowed_types)}.')

    def __eq__(self, other):
        return (
            isinstance(other, MimeTypeValidator) and
            set(self.allowed_types) == set(other.allowed_types)
        )

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash(MimeTypeValidator) + 7 * hash(self.allowed_types)

@deconstructible
class ContainerImageValidator(object):
    single_image = True

    def __init__(self, *, single_image: bool = True):
        self.single_image = single_image
        super(ContainerImageValidator, self).__init__()

    def __call__(self, value):
        # value should be a tar archive with manifest.json at the root

        # Reopen the file, but do not close as django opens it again later
        value.open(mode='rb')
        try:
            with tarfile.open(fileobj=value, mode='r') as t:
                names = t.getnames()
                member = dict(zip(t.getnames(), t.getmembers()))[
                    'manifest.json']
                manifest = t.extractfile(member).read()
        except KeyError:
            raise ValidationError('manifest.json not found at the root of the '
                                  'container image file. Was this created '
                                  'with docker save? '
                                  f'{names}')

        manifest = json.loads(manifest)
        if self.single_image and len(manifest) != 1:
            raise ValidationError('The container image file should only have '
                                  '1 image. This file contains '
                                  f'{len(manifest)}.')

    def __eq__(self, other):
        return (
            isinstance(other, ContainerImageValidator) and
            self.single_image == other.single_image
        )

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash(ContainerImageValidator) + 7 * hash(self.single_image)
