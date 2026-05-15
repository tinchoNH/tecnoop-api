from pydantic import BaseModel
from typing import Optional

class ClienteCreate(BaseModel):
    razon_social: str
    cuit: Optional[str] = None
    responsable: Optional[str] = None
    celular: Optional[str] = None
    email: Optional[str] = None
    direccion: Optional[str] = None
    localidad: Optional[str] = None

class ClienteUpdate(BaseModel):
    razon_social: Optional[str] = None
    cuit: Optional[str] = None
    responsable: Optional[str] = None
    celular: Optional[str] = None
    email: Optional[str] = None
    direccion: Optional[str] = None
    localidad: Optional[str] = None

class SedeCreate(BaseModel):
    nombre: str
    direccion: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    contacto_sede: Optional[str] = None
    celular_sede: Optional[str] = None

class SedeUpdate(BaseModel):
    nombre: Optional[str] = None
    direccion: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    contacto_sede: Optional[str] = None
    celular_sede: Optional[str] = None
