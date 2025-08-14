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

# endpoint to post a new event
@router.post("/events")
async def post_event(request: Request, db: AsyncSession = Depends(get_db)):
    payload_event = await request.json()
    is_valid, errors = validate_payload_event(payload_event)
    if not is_valid:
        return JSONResponse(content={"errors": errors}, status_code=400)

    # get the current UTC time in ISO 8601 format
    current_iso_utc = datetime.now(timezone.utc).isoformat()
    timestamp = datetime.fromisoformat(current_iso_utc)
    # generate a unique UUID for the event
    eventid = uuid4()

    # Add ingestedAt and eventId fields also to the event payload
    payload_event["ingestedAt"] = current_iso_utc
    payload_event["eventId"] = str(eventid)

    # create an AuditEvent model instance and add to db
    db_event = AuditEvent(event=payload_event, ingestedat=timestamp, eventid=eventid)
    db.add(db_event)
    await db.commit()

    # publish the event to Redis (for real-time streaming clients)
    await redis_client.publish(REDIS_CHANNEL, json.dumps(payload_event))

    return JSONResponse(content={"message": "Success!"}, status_code=201)



# endpoint to retrieve a single event by ID
@router.get("/events/{event_id}")
async def get_event(event_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AuditEvent).where(AuditEvent.eventid == event_id))
    event = result.scalar_one_or_none()
    if event is None:
        return JSONResponse(content={"message": "Event not found!"}, status_code=404)
    return event



# endpoint to retrieve all events
@router.get("/events")
async def get_all_events(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AuditEvent).order_by(AuditEvent.ingestedat))
    events = result.scalars().all()
    return [e.event for e in events]



# endpoint to stream events in real-time using SSE using Redis Pub/Sub as the event source
@router.get("/stream")
async def stream_events():
    # create a Redis Pub/Sub subscriber
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(REDIS_CHANNEL)

     # inner generator function to continuously stream events
    async def event_stream():
        try:
            while True:
                # get the next message from Redis, waiting up to 10 seconds
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=10)
                if message and message['type'] == 'message':
                    data = message['data']
                    # format the message for SSE
                    yield f"data: {data}\n\n"
                else:
                    # avoid busy looping
                    await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            # cleanup if the client disconnects
            await pubsub.unsubscribe(REDIS_CHANNEL)
            await pubsub.close()

    # return a streaming HTTP response for SSE clients
    return StreamingResponse(event_stream(), media_type="text/event-stream")
