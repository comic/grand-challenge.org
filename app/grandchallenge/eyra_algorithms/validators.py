from django.core.exceptions import ValidationError

import requests
from django.conf import settings

def IdExistsInDockerRegistryValidator(value):
    resp = requests.get(f"https://{settings.PRIVATE_DOCKER_REGISTRY}/v2/_catalog")

    if not value in resp.json()['repositories']:
        raise ValidationError(
            f"Id {value} does not exist in database. "
            "Please push your algorithm container to the registry before filling in this form."
        )
