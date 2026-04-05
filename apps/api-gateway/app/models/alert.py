from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, ForeignKey, func, Enum
from app.database import Base
import enum


class SeverityLevel(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertStatus(str, enum.Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    threat_id = Column(String, unique=True, index=True)
    severity = Column(Enum(SeverityLevel), nullable=False)
    status = Column(Enum(AlertStatus), default=AlertStatus.OPEN)
    classification = Column(String, nullable=False)
    source_ip = Column(String)
    destination_ip = Column(String)
    source_port = Column(Integer)
    destination_port = Column(Integer)
    protocol = Column(String)
    confidence_score = Column(Float)
    raw_payload = Column(JSON)
    description = Column(String)
    acknowledged_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
