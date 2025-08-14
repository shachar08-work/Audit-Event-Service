import os
import time
import json
import redis.asyncio as redis
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from jsonschema import Draft7Validator, FormatChecker
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from sqlalchemy import delete
from sqlalchemy.exc import OperationalError

# Conditional imports for Docker vs local
RUNNING_IN_DOCKER = os.getenv("RUNNING_IN_DOCKER", "false").lower() == "true"
if RUNNING_IN_DOCKER:
    from src.models import Base, AuditEvent
    from src.database import async_session, init_engine
else:
    from models import Base, AuditEvent
    from database import async_session, init_engine

# Redis configuration
REDIS_HOST = "redis" if RUNNING_IN_DOCKER else "localhost"
REDIS_PORT = 6379 if RUNNING_IN_DOCKER else int(os.getenv("REDIS_PORT", 6379))
REDIS_CHANNEL = "audit_events_channel"

# Redis client
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# Load JSON schema
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_PATH = os.path.join(BASE_DIR, "audit_log_schema.json")
with open(SCHEMA_PATH) as f:
    audit_schema = json.load(f)

validator = Draft7Validator(audit_schema, format_checker=FormatChecker())

def validate_payload_event(payload_event):
    errors = []
    for error in validator.iter_errors(payload_event):
        errors.append([list(error.path), str(error.message)])
    return len(errors) == 0, errors

async def delete_old_events():
    async with async_session() as session:
        cutoff = datetime.now(timezone.utc) - relativedelta(years=3)
        stmt = delete(AuditEvent).where(AuditEvent.ingestedat < cutoff)
        await session.execute(stmt)
        await session.commit()

def schedule_cleanup():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(delete_old_events, 'cron', hour=0, minute=0, timezone='UTC')
    scheduler.start()
    print("Scheduler started. Cleanup runs every 24 hours at 00:00 UTC time.")


# Synchronous table creation to ensure tables exist before app runs.
def init_tables_sync():
    while True:
        try:
            with init_engine.connect() as conn:
                Base.metadata.create_all(conn)
                conn.commit()
                break
        except OperationalError:
            print("Postgres not ready, retrying in 2 seconds...")
            time.sleep(2)
