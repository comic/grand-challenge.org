import logging

import jwt
from django.conf import settings
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from health_imaging.models import Payload
from starlette import status

logger = logging.getLogger(__name__)

# TODO fill out the correct url
JWT_SCHEME = Depends(OAuth2PasswordBearer(tokenUrl="token"))


def get_validated_payload(token: str = JWT_SCHEME):
    try:
        payload = jwt.decode(
            jwt=token,
            audience=settings.HEALTH_IMAGING_JWT_AUDIENCE,
            issuer=settings.HEALTH_IMAGING_JWT_ISSUER,
            key=settings.HEALTH_IMAGING_JWT_PUBLIC_KEY,
            algorithms=[
                settings.HEALTH_IMAGING_JWT_ALGORTIHM,
            ],
            options={"require": ["exp", "iss", "aud"]},
        )
    except jwt.PyJWTError as error:
        logger.info(f"Invalid token: {error}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return Payload(**payload)


VALIDATED_PAYLOAD = Depends(get_validated_payload)
