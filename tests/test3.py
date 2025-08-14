import asyncio
import json
from pathlib import Path
import httpx
import time
import sys
from pathlib import Path
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Request, Depends

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.database import async_session, get_db
from src.models import Base, AuditEvent
from sqlalchemy import text
from sqlalchemy import delete
from sqlalchemy import select


API_URL = "http://127.0.0.1:8000/events"
NUM_WORKERS = 10
events_file = Path(__file__).parent / "valid_events.json"

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

# Load events: flatten the outer list since each inner list contains one event
with open(events_file, "r", encoding="utf-8") as f:
    raw_events = json.load(f)
events = [inner[0] for inner in raw_events]  # get the actual event dicts

async def post_event(client, event, worker_id, index):
    try:
        resp = await client.post(API_URL, json=event)
        if resp.status_code not in [200, 201]:
            print(f"[Worker {worker_id}] Event #{index} failed: {resp.status_code}, {resp.text}")
    except Exception as e:
        print(f"[Worker {worker_id}] Event #{index} exception: {e}")

async def worker(worker_id):
    async with httpx.AsyncClient() as client:
        for i, event in enumerate(events, start=1):
            await post_event(client, event, worker_id, i)

async def delete_all_events():
    async with async_session() as session:
        async with session.begin():
            await session.execute(delete(AuditEvent))  # Deletes all rows
        await session.commit()
    print("All events deleted.")

async def get_num_of_events():
    # Use async_session directly outside of FastAPI
    async with async_session() as session:
        result = await session.execute(select(AuditEvent).order_by(AuditEvent.ingestedat))
        events = result.scalars().all()
        return len(events)

async def main():
    # Create NUM_WORKERS async workers
    await delete_all_events()
    time.sleep(1)
    print("Cleared table successfully!")
    tasks = [asyncio.create_task(worker(i+1)) for i in range(NUM_WORKERS)]
    await asyncio.gather(*tasks)
    time.sleep(1)
    num_of_events = await get_num_of_events()
    assert (NUM_WORKERS*len(events)) == num_of_events, \
            f"{RED}Failed to create {NUM_WORKERS*len(events)} events with {NUM_WORKERS} threads!"
    print(f"{GREEN}✅ Created {num_of_events} events with {NUM_WORKERS} threads successfully!")
    

if __name__ == "__main__":
    asyncio.run(main())
