from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from database.database import get_db
from database.models.user import User
from sqlalchemy.orm import Session

from jose import jwt, jwk
import os
import base64
import requests
from dotenv import load_dotenv

security = HTTPBearer()

# Carichiamo esplicitamente il file .env per evitare problemi di import order
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path=env_path, override=True)

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")

# Decodifica la chiave base64 se usata per HS256
try:
    if SUPABASE_JWT_SECRET:
        clean_secret = SUPABASE_JWT_SECRET.strip()
        rem = len(clean_secret) % 4
        if rem > 0:
            clean_secret += "=" * (4 - rem)
        SUPABASE_JWT_SECRET_BYTES = base64.b64decode(clean_secret)
    else:
        SUPABASE_JWT_SECRET_BYTES = b""
except Exception as e:
    SUPABASE_JWT_SECRET_BYTES = SUPABASE_JWT_SECRET.encode()

# Cache per le chiavi JWKS
JWKS_CACHE = None

def get_jwks():
    global JWKS_CACHE
    if JWKS_CACHE is not None:
        return JWKS_CACHE
    
    if not SUPABASE_URL:
        print("WARNING: SUPABASE_URL non è definito nel file .env!")
        return None
        
    jwks_url = f"{SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
    try:
        res = requests.get(jwks_url, timeout=5)
        res.raise_for_status()
        JWKS_CACHE = res.json()
        return JWKS_CACHE
    except requests.exceptions.SSLError:
        # Fallback per proxy aziendali che sostituiscono i certificati SSL
        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            res = requests.get(jwks_url, timeout=5, verify=False)
            res.raise_for_status()
            JWKS_CACHE = res.json()
            return JWKS_CACHE
        except Exception as err:
            print("ERROR: Impossibile scaricare le JWKS anche disabilitando la verifica SSL:", err)
            return None
    except Exception as e:
        print("ERROR: Errore durante il download delle JWKS di Supabase:", e)
        return None

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials
    try:
        # Leggiamo l'header non verificato per capire l'algoritmo (ES256 o HS256)
        header = jwt.get_unverified_header(token)
        alg = header.get("alg")
        kid = header.get("kid")

        payload = None

        if alg == "ES256":
            # Autenticazione moderna asimmetrica (JWKS)
            jwks = get_jwks()
            if not jwks or "keys" not in jwks:
                # Se fallisce, forziamo un tentativo di scaricamento pulito
                global JWKS_CACHE
                JWKS_CACHE = None
                jwks = get_jwks()

            if not jwks or "keys" not in jwks:
                raise Exception("JWKS non disponibili per validare la firma")

            key_data = next((k for k in jwks["keys"] if k["kid"] == kid), None)
            if not key_data:
                # Se non troviamo il kid, forse le chiavi sono ruotate, forziamo ricaricamento
                JWKS_CACHE = None
                jwks = get_jwks()
                key_data = next((k for k in jwks["keys"] if k["kid"] == kid), None)

            if not key_data:
                raise Exception(f"Chiave kid '{kid}' non trovata nella JWKS di Supabase")

            # Costruiamo la chiave pubblica e verifichiamo la firma
            public_key = jwk.construct(key_data)
            payload = jwt.decode(
                token,
                public_key.to_pem(),
                algorithms=["ES256"],
                options={"verify_aud": False}
            )

        elif alg == "HS256":
            # Autenticazione simmetrica legacy
            try:
                payload = jwt.decode(
                    token,
                    SUPABASE_JWT_SECRET_BYTES,
                    algorithms=["HS256"],
                    options={"verify_aud": False}
                )
            except Exception as e1:
                payload = jwt.decode(
                    token,
                    SUPABASE_JWT_SECRET,
                    algorithms=["HS256"],
                    options={"verify_aud": False}
                )
        else:
            raise Exception(f"Algoritmo di firma '{alg}' non supportato")

        if not payload:
            raise Exception("Decodifica del payload fallita")

        # In Supabase, 'sub' è l'UUID dell'utente
        auth0_id = payload.get("sub")

        # ✅ 🔥 PRENDI I RUOLI DA SUPABASE (app_metadata)
        app_metadata = payload.get("app_metadata", {})
        roles = app_metadata.get("roles", [])
        
        # Determina il ruolo primario da associare nel DB
        primary_role = "USER"
        if "ADMIN" in roles:
            primary_role = "ADMIN"
        elif "TREASURER" in roles:
            primary_role = "TREASURER"
        elif "SECRETARY" in roles:
            primary_role = "SECRETARY"
        elif "MEMBER" in roles:
            primary_role = "MEMBER"
            
        # ✅ DB lookup (continuiamo a usare la colonna auth0_id per compatibilità col DB esistente)
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
            # Allinea il ruolo nel DB se è cambiato su Supabase
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

