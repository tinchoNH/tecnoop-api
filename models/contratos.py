from pydantic import BaseModel
from typing import Optional
from datetime import date


class ContratoCreate(BaseModel):
    cliente_id: str
    sede_id: Optional[str] = None
    tipo_servicio: str
    frecuencia: str   # diaria | semanal | quincenal | mensual | anual
    dia_semana: Optional[int] = None   # 0-6 si es semanal
    dia_mes: Optional[int] = None      # 1-31 si es mensual
    tecnico_id: Optional[str] = None
    tecnicos_ids: Optional[list] = []
    inicio: date
    fin: Optional[date] = None
    excluir_fines_semana: Optional[bool] = False


class ContratoUpdate(BaseModel):
    tecnico_id: Optional[str] = None
    tecnicos_ids: Optional[list] = None
    activo: Optional[bool] = None
    fin: Optional[date] = None
    excluir_fines_semana: Optional[bool] = None
