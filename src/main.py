import os
from fastapi import FastAPI

# Conditional imports for Docker vs local
RUNNING_IN_DOCKER = os.getenv("RUNNING_IN_DOCKER", "false").lower() == "true"
if RUNNING_IN_DOCKER:
    from src.routes import router
    from src.utils import schedule_cleanup, redis_client, init_tables_sync
else:
    from routes import router
    from utils import schedule_cleanup, redis_client, init_tables_sync



app = FastAPI()

# Include API routes
app.include_router(router)

@app.on_event("startup")
def on_startup():
    # Ensure tables exist before app runs
    init_tables_sync()
    # Start cleanup scheduler
    schedule_cleanup()

@app.on_event("shutdown")
async def on_shutdown():
    await redis_client.close()
    print("Redis connection closed. Shutdown complete.")
