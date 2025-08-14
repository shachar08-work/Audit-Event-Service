import sys
from pathlib import Path
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Request, Depends
from sqlalchemy import text, delete, select

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.database import async_session, get_db
from src.models import Base, AuditEvent
from src.utils import redis_client

import asyncio
import json
from datetime import datetime

GREEN = "\033[92m"

STREAM_NAME = "audit_events"
events_file = Path(__file__).parent / "valid_events.json"

# Load events: flatten the outer list since each inner list contains one event
with open(events_file, "r", encoding="utf-8") as f:
    raw_events = json.load(f)
events = [inner[0] for inner in raw_events]  # get the actual event dicts



async def post_event(r, start_index, count):
    for i in range(start_index - 1, start_index - 1 + count):
        event = events[i]
        await r.xadd(STREAM_NAME, {"event": json.dumps(event)})
        print(f"Pushed: {event['message']}")


async def read_stream(r):
    events = await r.xrange(STREAM_NAME)
    print(f"Stream '{STREAM_NAME}' has {len(events)} events:")
    for e_id, data in events:
        # use string key instead of bytes
        key = "event" if "event" in data else b"event"
        event = json.loads(data[key])
        print(f" - {event['message']}")
    return len(events)


async def main():
    await redis_client.delete(STREAM_NAME)
    print("=== First push 10 events ===")
    await post_event(redis_client, 1, 10)

    print("\n=== Check first stream ===")
    count1 = await read_stream(redis_client)

    assert count1 == 10, f"Expected 10 events, got {count1}"

    print("\n=== Push 10 more events ===")
    await post_event(redis_client, 1, 10)

    print("\n=== Check second stream ===")
    count2 = await read_stream(redis_client)

    assert count2 == 20, f"Expected 20 events, got {count2}"
    print(f"{GREEN}\n✅ Stream test passed!")


if __name__ == "__main__":
    asyncio.run(main())
