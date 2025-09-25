import logging

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from health_imaging import settings
from health_imaging.models import HealthImagingJWTPayload
from starlette import status

logger = logging.getLogger(__name__)

# TODO fill out the correct url
JWT_SCHEME = Depends(OAuth2PasswordBearer(tokenUrl="token"))


def get_validated_payload(token: str = JWT_SCHEME):
    try:
        payload = jwt.decode(
            jwt=token,
            options={"require": ["exp", "iss", "aud"]},
            issuer=settings.HEALTH_IMAGING_JWT_ISSUER,
            audience=settings.HEALTH_IMAGING_JWT_AUDIENCE,
            key=settings.HEALTH_IMAGING_JWT_PUBLIC_KEY,
            algorithms=[
                settings.HEALTH_IMAGING_JWT_ALGORITHM,
            ],
        )
    except jwt.PyJWTError as error:
        logger.info(f"Invalid token: {error}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return HealthImagingJWTPayload(**payload)


VALIDATED_PAYLOAD = Depends(get_validated_payload)
