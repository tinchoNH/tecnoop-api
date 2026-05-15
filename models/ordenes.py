from pydantic import BaseModel
from typing import Optional, List
from datetime import date


class OrdenCreate(BaseModel):
    cliente_id:       str
    sede_id:          str
    tipo_servicio:    str
    descripcion:      Optional[str]  = None
    fecha_programada: date
    hora_inicio:      Optional[str]  = None   # "HH:MM"
    tecnico_id:       Optional[str]  = None
    contrato_id:      Optional[str]  = None
    checklist:        Optional[list] = []


class OrdenUpdate(BaseModel):
    cliente_id:       Optional[str]  = None
    sede_id:          Optional[str]  = None
    tecnico_id:       Optional[str]  = None
    tipo_servicio:    Optional[str]  = None
    descripcion:      Optional[str]  = None
    fecha_programada: Optional[date] = None
    hora_inicio:      Optional[str]  = None
    observaciones:    Optional[str]  = None
    fotos:            Optional[List[str]] = None
    checklist:        Optional[list] = None
    firma_url:        Optional[str]  = None
    pdf_url:          Optional[str]  = None
    factura_id:       Optional[str]  = None


class CambioEstado(BaseModel):
    estado: str


ESTADOS_VALIDOS = {
    "pendiente": ["asignada", "cancelada"],
    "asignada":  ["en_curso", "cancelada"],
    "en_curso":  ["realizada", "cancelada"],
    "realizada": [],
    "cancelada": [],
}
