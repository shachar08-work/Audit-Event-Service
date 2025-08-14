import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()
RUNNING_IN_DOCKER = os.getenv("RUNNING_IN_DOCKER", "false").lower() == "true"

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = 5432 if RUNNING_IN_DOCKER else int(os.getenv("DB_PORT", 5432))

DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@postgres:{DB_PORT}/{DB_NAME}"
INIT_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@postgres:{DB_PORT}/{DB_NAME}"

init_engine = create_engine(INIT_DATABASE_URL)

engine = create_async_engine(DATABASE_URL, echo=True, future=True)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_db():
    async with async_session() as session:
        yield session



