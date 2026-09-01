from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from pydantic import BaseModel
from typing import Optional, List
import csv, io
from datetime import UTC, datetime

from app.database import get_db
from app.models.alert import Alert, AlertStatus, SeverityLevel
from app.models.user import User
from app.core.security import get_current_active_user

router = APIRouter()


class AlertResponse(BaseModel):
    id: int
    threat_id: str
    severity: SeverityLevel
    status: AlertStatus
    classification: str
    source_ip: Optional[str]
    destination_ip: Optional[str]
    source_port: Optional[int]
    destination_port: Optional[int]
    protocol: Optional[str]
    confidence_score: Optional[float]
    description: Optional[str]
    acknowledged_by: Optional[int]
    acknowledged_at: Optional[datetime]
    resolved_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class AlertStats(BaseModel):
    total: int
    critical: int
    high: int
    medium: int
    low: int
    open: int
    acknowledged: int
    resolved: int


class AcknowledgeRequest(BaseModel):
    note: Optional[str] = None


@router.get("", response_model=List[AlertResponse])
async def list_alerts(
    severity: Optional[SeverityLevel] = None,
    status: Optional[AlertStatus] = None,
    q: Optional[str] = Query(None, description="Search by classification, source IP or description"),
    limit: int = Query(50, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    query = select(Alert).order_by(desc(Alert.created_at)).limit(limit).offset(offset)
    if severity:
        query = query.where(Alert.severity == severity)
    if status:
        query = query.where(Alert.status == status)
    if q:
        from sqlalchemy import or_
        like = f"%{q}%"
        query = query.where(
            or_(
                Alert.classification.ilike(like),
                Alert.source_ip.ilike(like),
                Alert.destination_ip.ilike(like),
                Alert.description.ilike(like),
            )
        )

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/stats", response_model=AlertStats)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    result = await db.execute(select(Alert))
    alerts = result.scalars().all()

    return AlertStats(
        total=len(alerts),
        critical=sum(1 for a in alerts if a.severity == SeverityLevel.CRITICAL),
        high=sum(1 for a in alerts if a.severity == SeverityLevel.HIGH),
        medium=sum(1 for a in alerts if a.severity == SeverityLevel.MEDIUM),
        low=sum(1 for a in alerts if a.severity == SeverityLevel.LOW),
        open=sum(1 for a in alerts if a.status == AlertStatus.OPEN),
        acknowledged=sum(1 for a in alerts if a.status == AlertStatus.ACKNOWLEDGED),
        resolved=sum(1 for a in alerts if a.status == AlertStatus.RESOLVED),
    )


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.patch("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: int,
    body: AcknowledgeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = AlertStatus.ACKNOWLEDGED
    alert.acknowledged_by = current_user.id
    alert.acknowledged_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(alert)
    return alert


@router.patch("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = AlertStatus.RESOLVED
    alert.resolved_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(alert)
    return alert


@router.get("/export")
async def export_alerts_csv(
    severity: Optional[SeverityLevel] = None,
    status: Optional[AlertStatus] = None,
    limit: int = Query(1000, le=5000),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    """Export alerts as CSV for offline analysis."""
    from fastapi.responses import StreamingResponse
    query = select(Alert).order_by(desc(Alert.created_at)).limit(limit)
    if severity:
        query = query.where(Alert.severity == severity)
    if status:
        query = query.where(Alert.status == status)
    result = await db.execute(query)
    alerts = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "threat_id", "severity", "status", "classification",
        "source_ip", "source_port", "destination_ip", "destination_port",
        "protocol", "confidence_score", "description", "created_at"
    ])
    for a in alerts:
        writer.writerow([
            a.id, a.threat_id, a.severity.value, a.status.value,
            a.classification, a.source_ip, a.source_port,
            a.destination_ip, a.destination_port, a.protocol,
            a.confidence_score, a.description,
            a.created_at.isoformat() if a.created_at else "",
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=alerts.csv"},
    )
