import os
import json
import asyncio
from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Conditional imports for Docker vs local
RUNNING_IN_DOCKER = os.getenv("RUNNING_IN_DOCKER", "false").lower() == "true"
if RUNNING_IN_DOCKER:
    from src.database import get_db
    from src.models import AuditEvent
    from src.utils import validate_payload_event, redis_client, REDIS_CHANNEL
else:
    from database import get_db
    from models import AuditEvent
    from utils import validate_payload_event, redis_client, REDIS_CHANNEL

router = APIRouter()

@router.post("/events")
async def post_event(request: Request, db: AsyncSession = Depends(get_db)):
    payload_event = await request.json()
    is_valid, errors = validate_payload_event(payload_event)
    if not is_valid:
        return JSONResponse(content={"errors": errors}, status_code=400)

    current_iso_utc = datetime.now(timezone.utc).isoformat()
    timestamp = datetime.fromisoformat(current_iso_utc)
    eventid = uuid4()

    payload_event["ingestedAt"] = current_iso_utc
    payload_event["eventId"] = str(eventid)

    db_event = AuditEvent(event=payload_event, ingestedat=timestamp, eventid=eventid)
    db.add(db_event)
    await db.commit()

    # Publish event to Redis
    await redis_client.publish(REDIS_CHANNEL, json.dumps(payload_event))
    return JSONResponse(content={"message": "Success!"}, status_code=201)

@router.get("/events/{event_id}")
async def get_event(event_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AuditEvent).where(AuditEvent.eventid == event_id))
    event = result.scalar_one_or_none()
    if event is None:
        return JSONResponse(content={"message": "Event not found!"}, status_code=404)
    return event

@router.get("/events")
async def get_all_events(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AuditEvent).order_by(AuditEvent.ingestedat))
    events = result.scalars().all()
    return [e.event for e in events]

@router.get("/stream")
async def stream_events():
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(REDIS_CHANNEL)

    async def event_stream():
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=10)
                if message and message['type'] == 'message':
                    data = message['data']
                    yield f"data: {data}\n\n"
                else:
                    await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            await pubsub.unsubscribe(REDIS_CHANNEL)
            await pubsub.close()

    return StreamingResponse(event_stream(), media_type="text/event-stream")
