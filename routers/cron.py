import os
from fastapi import APIRouter, Header, HTTPException
from services.cron import generar_ots_manana

router = APIRouter()

CRON_SECRET = os.getenv("CRON_SECRET", "")


@router.post("/generar-ots")
def cron_generar_ots(x_cron_secret: str = Header(default="")):
    if not CRON_SECRET or x_cron_secret != CRON_SECRET:
        raise HTTPException(401, "No autorizado")
    return generar_ots_manana()
