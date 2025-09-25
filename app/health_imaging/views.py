import gzip
import json

from fastapi import APIRouter, HTTPException
from health_imaging.auth import VALIDATED_PAYLOAD
from health_imaging.lifespan import CLIENTS
from health_imaging.models import Payload
from starlette.responses import StreamingResponse

router = APIRouter()


@router.get("/api/v1/cases/images/{image_set_id}/dicom/metadata/")
async def get_metadata(
    image_set_id: str,
    validated_payload: Payload = VALIDATED_PAYLOAD,
):
    if image_set_id != validated_payload.image_set_id:
        raise HTTPException(status_code=404, detail="Image not found")

    response = await CLIENTS["medical_imaging"].get_image_set_metadata(
        datastoreId=validated_payload.datastore_id,
        imageSetId=validated_payload.image_set_id,
    )

    metadata = json.loads(
        gzip.decompress(await response["imageSetMetadataBlob"].read())
    )

    return metadata


@router.get("/api/v1/cases/images/{image_set_id}/dicom/instances/{frame_id}/")
async def get_instances(
    image_set_id: str,
    frame_id: str,
    validated_payload: Payload = VALIDATED_PAYLOAD,
):
    if image_set_id != validated_payload.image_set_id:
        raise HTTPException(status_code=404, detail="Image not found")

    response = await CLIENTS["medical_imaging"].get_image_frame(
        datastoreId=validated_payload.datastore_id,
        imageSetId=validated_payload.image_set_id,
        imageFrameInformation={"imageFrameId": frame_id},
    )

    async def stream_response_chunks():
        async for chunk in response["imageFrameBlob"].iter_chunks():
            yield chunk

    return StreamingResponse(
        stream_response_chunks(), media_type=response["contentType"]
    )
