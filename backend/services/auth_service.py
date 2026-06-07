from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta

SECRET_KEY = "secret"
ALGORITHM = "HS256"

pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto"
)

def hash_password(password: str):
    return pwd_context.hash(password)

def verify(password, hashed):
    return pwd_context.verify(password, hashed)

def create_token(data: dict):
    data.update({"exp": datetime.utcnow() + timedelta(hours=2)})
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)