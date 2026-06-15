from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from database.database import get_db
from database.models.user import User
from sqlalchemy.orm import Session

from jose import jwt
import requests
import os

security = HTTPBearer()

AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN", "")
API_AUDIENCE = os.getenv("API_AUDIENCE", "")
#ALGORITHMS = ["RS256"]

#TODO in prod togliere  verify=False
jwks = requests.get(f"https://{AUTH0_DOMAIN}/.well-known/jwks.json", verify=False).json()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials

    try:
        # 🔐 decode JWT
        unverified_header = jwt.get_unverified_header(token)

        rsa_key = {}
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = key

        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=API_AUDIENCE,
            issuer=f"https://{AUTH0_DOMAIN}/"
        )

        auth0_id = payload.get("sub")

        # ✅ 🔥 PRENDI I RUOLI DA AUTH0
        roles = payload.get("https://aps/roles", [])

        # Determina il ruolo primario da associare nel DB
        primary_role = "USER"
        if "ADMIN" in roles:
            primary_role = "ADMIN"
        elif "TREASURER" in roles:
            primary_role = "TREASURER"
        elif "MEMBER" in roles:
            primary_role = "MEMBER"

        # ✅ DB lookup
        user = db.query(User).filter_by(auth0_id=auth0_id).first()

        if not user:
            user = User(
                auth0_id=auth0_id,
                status="INCOMPLETE",
                role=primary_role
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            # Allinea il ruolo nel DB se è cambiato su Auth0
            if user.role != primary_role:
                user.role = primary_role
                db.commit()
                db.refresh(user)

        # Allega tutti i ruoli all'oggetto user
        user.roles = roles

        return user

    except Exception as e:
        print("ERROR:", str(e))
        raise HTTPException(status_code=401, detail="Invalid token")

