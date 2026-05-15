from pydantic import BaseModel
from typing import Optional


class UsuarioCreate(BaseModel):
    nombre: str
    email: str
    password: str
    rol: str  # admin | supervisor | tecnico | cliente
    tecnico_id: Optional[str] = None


class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = None
    rol: Optional[str] = None
    tecnico_id: Optional[str] = None
    activo: Optional[bool] = None
