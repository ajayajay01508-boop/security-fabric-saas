from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid
import time

from app.services.kafka_service import kafka_producer
from app.core.security import get_current_active_user
from app.models.user import User

router = APIRouter()


class TelemetryEvent(BaseModel):
    source_ip: str
    destination_ip: str
    source_port: int
    destination_port: int
    protocol: str
    bytes_sent: int = 0
    bytes_received: int = 0
    packets: int = 0
    duration_ms: int = 0
    flags: Optional[str] = None
    payload_sample: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class TelemetryBatch(BaseModel):
    events: list[TelemetryEvent]


@router.post("/ingest")
async def ingest_event(
    event: TelemetryEvent,
    current_user: User = Depends(get_current_active_user),
):
    payload = {
        "event_id": str(uuid.uuid4()),
        "timestamp": time.time(),
        "tenant_id": current_user.id,
        **event.model_dump(),
    }
    await kafka_producer.send("raw-telemetry", payload)
    return {"status": "queued", "event_id": payload["event_id"]}


@router.post("/ingest/batch")
async def ingest_batch(
    batch: TelemetryBatch,
    current_user: User = Depends(get_current_active_user),
):
    if len(batch.events) > 1000:
        raise HTTPException(status_code=400, detail="Batch size exceeds limit of 1000")

    event_ids = []
    for event in batch.events:
        payload = {
            "event_id": str(uuid.uuid4()),
            "timestamp": time.time(),
            "tenant_id": current_user.id,
            **event.model_dump(),
        }
        await kafka_producer.send("raw-telemetry", payload)
        event_ids.append(payload["event_id"])

    return {"status": "queued", "count": len(event_ids), "event_ids": event_ids}
