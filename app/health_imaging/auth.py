import logging

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from health_imaging.models import Payload
from health_imaging.settings import settings
from starlette import status

logger = logging.getLogger(__name__)

JWT_SCHEME = Depends(OAuth2PasswordBearer(tokenUrl="token"))


def get_validated_payload(token: str = JWT_SCHEME):
    try:
        payload = jwt.decode(
            jwt=token,
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            key=settings.jwt_public_key,
            algorithms=[
                settings.jwt_algorithm,
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
