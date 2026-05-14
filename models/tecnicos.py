from pydantic import BaseModel
from typing import Optional, List
from datetime import date


class TecnicoCreate(BaseModel):
    nombre: str
    celular: Optional[str] = None
    email: Optional[str] = None
    vehiculo: Optional[str] = None
    zonas: Optional[List[str]] = []
    especialidades: Optional[List[str]] = []
    estado: Optional[str] = "disponible"
    horas_base: Optional[int] = 8
    ingreso: Optional[date] = None


class TecnicoUpdate(BaseModel):
    nombre: Optional[str] = None
    celular: Optional[str] = None
    email: Optional[str] = None
    vehiculo: Optional[str] = None
    zonas: Optional[List[str]] = None
    especialidades: Optional[List[str]] = None
    estado: Optional[str] = None
    horas_base: Optional[int] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
