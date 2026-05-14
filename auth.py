import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from database import get_db

router = APIRouter()
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24


class LoginRequest(BaseModel):
    email: str
    password: str


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency: valida JWT y retorna el payload con user_id, empresa_id, rol."""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")


@router.post("/login")
def login(body: LoginRequest):
    db = get_db()
    result = db.table("usuarios").select("*").eq("email", body.email).eq("activo", True).execute()

    if not result.data:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    user = result.data[0]

    if not pwd_context.verify(body.password, user["password"]):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    token = create_access_token({
        "user_id": user["id"],
        "empresa_id": user["empresa_id"],
        "rol": user["rol"],
        "nombre": user["nombre"],
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "nombre": user["nombre"],
            "email": user["email"],
            "rol": user["rol"],
            "empresa_id": user["empresa_id"],
        }
    }
