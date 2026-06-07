from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.database import get_db
from dependencies.auth import get_current_user
from database.models.audit import AuditLog

router = APIRouter()


@router.get("/")
def get_audit_logs(user=Depends(get_current_user), db: Session = Depends(get_db)):

    if user.role not in ["ADMIN", "TREASURER"]:
        raise HTTPException(403, "Forbidden")

    return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()