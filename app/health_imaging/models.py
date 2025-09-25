from datetime import datetime

from pydantic import BaseModel


class HealthImagingJWTPayload(BaseModel):
    # Registered Claims
    exp: datetime  # Expiration Time
    iss: str  # Issuer
    aud: list[str]  # Audience
    # Private Claims
    image_set_id: str
