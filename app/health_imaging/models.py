from datetime import datetime

from pydantic import BaseModel


class Payload(BaseModel):
    # Registered Claims
    exp: datetime  # Expiration Time
    iss: str  # Issuer
    aud: list[str]  # Audience
    # Private Claims
    datastore_id: str
    image_set_id: str
