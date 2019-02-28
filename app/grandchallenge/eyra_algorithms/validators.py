from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible

import requests
from django.conf import settings

@deconstructible
class IdExistsInDockerRegistryValidator(object):
    def __call__(self, value):
        resp = requests.get(f"{settings.PRIVATE_DOCKER_REGISTRY}/v2/_catalog")

        if not value in resp.json()['repositories']:
            raise ValidationError(
                f"Id {value} does not exist in database. "
                "Please push your algorithm container to the registry before filling in this form."
            )

    def __eq__(self, other):
        return (
            isinstance(other, IdExistsInDockerRegistryValidator)
            and self.schema == other.schema
        )

    def __ne__(self, other):
        return not (self == other)