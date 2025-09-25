import os
from base64 import b64decode

AWS_DEFAULT_REGION = os.environ.get("AWS_DEFAULT_REGION", "eu-central-1")
AWS_HEALTH_IMAGING_DATASTORE_ID = os.environ.get(
    "AWS_HEALTH_IMAGING_DATASTORE_ID", ""
)

HEALTH_IMAGING_JWT_AUDIENCE = os.environ.get(
    "HEALTH_IMAGING_JWT_AUDIENCE",
    "urn:grand-challenge-health-imaging",  # TODO Should be a URI
)
HEALTH_IMAGING_JWT_ISSUER = os.environ.get(
    "HEALTH_IMAGING_JWT_ISSUER",
    "urn:grand-challenge-django-api",  # TODO Should be a URI
)
HEALTH_IMAGING_JWT_ALGORITHM = os.environ.get(
    "HEALTH_IMAGING_JWT_ALGORITHM", "RS256"
)
HEALTH_IMAGING_JWT_PUBLIC_KEY = b64decode(
    os.environ.get("HEALTH_IMAGING_JWT_PUBLIC_KEY_BASE64", "").encode("ascii")
)
