import base64
import logging

import boto3
from django.conf import settings

logger = logging.getLogger(__name__)


def _get_registry_auth_config():
    if settings.COMPONENTS_REGISTRY_INSECURE:
        logger.warning("Refusing to provide credentials to insecure registry")
        return None
    else:
        client = boto3.client(
            "ecr", region_name=settings.COMPONENTS_AMAZON_ECR_REGION
        )
        auth = client.get_authorization_token()

        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecr.html#ECR.Client.get_authorization_token
        b64_user_token = auth["authorizationData"][0]["authorizationToken"]
        b64_user_token_bytes = b64_user_token.encode("ascii")
        user_token = base64.b64decode(b64_user_token_bytes).decode("ascii")
        username, token = user_token.split(":")

        # Matches format used in docker\api\image.py::ImageApiMixin:pull
        return {"username": username, "password": token}
