from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from database import get_db
from firebase_auth import authenticated_user
from models import NotificationDevice
from services.notification_service import enforce_registration_rate_limit, register_device

router = APIRouter(prefix="/api/v1/devices", tags=["Devices"])

class DeviceRegistration(BaseModel):
    platform: str
    deviceId: str = Field(min_length=1, max_length=160)
    fcmToken: str = Field(min_length=20, max_length=4096)
    appVersion: str | None = Field(default=None, max_length=40)

@router.post("/register")
def register(body: DeviceRegistration, user=Depends(authenticated_user), db: Session=Depends(get_db)):
    enforce_registration_rate_limit(db, user.id)
    row = register_device(db, user=user, platform=body.platform, device_identifier=body.deviceId,
                          fcm_token=body.fcmToken, app_version=body.appVersion)
    db.commit()
    return {"deviceId": row.id, "active": row.active}

@router.delete("/{device_id}", status_code=204)
def unregister(device_id: str, user=Depends(authenticated_user), db: Session=Depends(get_db)):
    row = db.query(NotificationDevice).filter_by(id=device_id, user_id=user.id).first()
    if row is None:
        raise HTTPException(404, "Device not found")
    row.active = False
    row.invalidated_at = datetime.now(timezone.utc)
    db.commit()
