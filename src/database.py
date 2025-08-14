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


# synchronous SQLAlchemy engine used for initialization tasks (creating table)
init_engine = create_engine(INIT_DATABASE_URL)

# asynchronous SQLAlchemy engine for regular app operations
engine = create_async_engine(DATABASE_URL, echo=True, future=True)
# session factory for async database session
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Dependency for FastAPI routes that need a database session
# Automatically opens and closes an async DB session for each request
async def get_db():
    async with async_session() as session:
        yield session



