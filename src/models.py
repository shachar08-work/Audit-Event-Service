from sqlalchemy import Column, TIMESTAMP, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class AuditEvent(Base):
    __tablename__ = "audit_events_table"

    eventid = Column(UUID(as_uuid=True), primary_key=True)
    ingestedat = Column(TIMESTAMP(timezone=True), nullable=False)
    event = Column(JSON, nullable=False)