from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.database import get_db
from dependencies.auth import get_current_user
from services.dashboard_service import get_treasurer_dashboard

router = APIRouter()


@router.get("/")
def dashboard(user=Depends(get_current_user), db: Session = Depends(get_db)):

    if user.role != "TREASURER":
        raise HTTPException(status_code=403, detail="Forbidden")

    return get_treasurer_dashboard(db)