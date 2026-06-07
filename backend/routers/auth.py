from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from database.database import get_db
from database.models.user import User
from dependencies.auth import get_current_user
from services.auth_service import hash_password, verify, create_token

router = APIRouter()

#  REGISTER LOCALE
@router.post("/register")
def register(email: str, password: str, db: Session = Depends(get_db)):

    existing = db.query(User).filter_by(email=email).first()

    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    user = User(
        email=email,
        password_hash=hash_password(password),
        role="USER",
        status="INCOMPLETE"
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {"msg": "User created"}


#  LOGIN LOCALE
@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):

    user = db.query(User).filter_by(email=form_data.username).first()

    if not user or not verify(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token({"id": user.id})

    return {
        "access_token": token,
        "token_type": "bearer"
    }


#  LOGIN GOOGLE
@router.post("/google")
def google_login(token: str, db: Session = Depends(get_db)):

    from google.oauth2 import id_token
    from google.auth.transport import requests

    GOOGLE_CLIENT_ID = "TUO_CLIENT_ID"

    try:
        idinfo = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            GOOGLE_CLIENT_ID
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    email = idinfo["email"]
    google_id = idinfo["sub"]

    user = db.query(User).filter_by(email=email).first()

    # ✅ CASO 1: utente NON esiste → crealo
    if not user:
        user = User(
            email=email,
            google_id=google_id,
            status="INCOMPLETE"
        )
        db.add(user)

    else:
        # ✅ CASO 2: utente esiste MA NON ha google_id → collega
        if not user.google_id:
            user.google_id = google_id

    db.commit()
    db.refresh(user)

    token = create_token({"id": user.id})

    return {
        "access_token": token,
        "token_type": "bearer",
        "status": user.status
    }