from contextlib import asynccontextmanager

import aioboto3
from health_imaging import settings

CLIENTS = {}


@asynccontextmanager
async def lifespan(*_, **__):
    session = aioboto3.Session(
        region_name=settings.AWS_DEFAULT_REGION,
    )

    # The client needs to exist for the lifetime of the FastAPI process
    # in order for StreamingResponse to work
    async with session.client("medical-imaging") as client:
        CLIENTS["medical_imaging"] = client
        yield
        del CLIENTS["medical_imaging"]
