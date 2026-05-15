from fastapi import APIRouter, Depends
from datetime import date, timedelta
from auth import verify_token
from middleware.tenant import get_empresa_id
from database import get_db

router = APIRouter()

DIAS_ES = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


@router.get("/dashboard")
def dashboard(token=Depends(verify_token)):
    empresa_id = get_empresa_id(token)
    db = get_db()
    hoy = date.today()
    ayer = hoy - timedelta(days=1)

    # OTs de hoy
    r_hoy = (
        db.table("ordenes_trabajo")
        .select("id, estado, tecnico_id, tecnicos(id, nombre, estado)")
        .eq("empresa_id", empresa_id)
        .eq("fecha_programada", hoy.isoformat())
        .execute()
    )
    ots_hoy = r_hoy.data or []

    estados_hoy = {"en_curso": 0, "realizadas": 0, "pendientes": 0, "canceladas": 0}
    sin_asignar = 0
    tecnicos_map: dict[str, dict] = {}

    for ot in ots_hoy:
        estado = ot["estado"]
        if estado == "en_curso":
            estados_hoy["en_curso"] += 1
        elif estado == "realizada":
            estados_hoy["realizadas"] += 1
        elif estado in ("pendiente", "asignada"):
            estados_hoy["pendientes"] += 1
        elif estado == "cancelada":
            estados_hoy["canceladas"] += 1

        if not ot.get("tecnico_id"):
            sin_asignar += 1

        tec = ot.get("tecnicos")
        if tec:
            tid = tec["id"]
            if tid not in tecnicos_map:
                tecnicos_map[tid] = {
                    "nombre": tec["nombre"],
                    "estado": tec["estado"],
                    "realizadas": 0,
                    "total": 0,
                }
            tecnicos_map[tid]["total"] += 1
            if estado == "realizada":
                tecnicos_map[tid]["realizadas"] += 1

    # OTs de ayer (solo total)
    r_ayer = (
        db.table("ordenes_trabajo")
        .select("id", count="exact")
        .eq("empresa_id", empresa_id)
        .eq("fecha_programada", ayer.isoformat())
        .neq("estado", "cancelada")
        .execute()
    )
    ots_ayer_total = r_ayer.count if r_ayer.count is not None else len(r_ayer.data or [])

    # OTs últimos 7 días para el gráfico
    desde = (hoy - timedelta(days=6)).isoformat()
    r_semana = (
        db.table("ordenes_trabajo")
        .select("fecha_programada, estado")
        .eq("empresa_id", empresa_id)
        .gte("fecha_programada", desde)
        .lte("fecha_programada", hoy.isoformat())
        .execute()
    )

    # Agrupar por fecha
    semana_map: dict[str, dict] = {}
    for i in range(7):
        d = hoy - timedelta(days=6 - i)
        key = d.isoformat()
        label = "Hoy" if d == hoy else DIAS_ES[d.weekday()]
        semana_map[key] = {"dia": label, "realizadas": 0, "pendientes": 0}

    for ot in (r_semana.data or []):
        key = ot["fecha_programada"]
        if key not in semana_map:
            continue
        if ot["estado"] == "realizada":
            semana_map[key]["realizadas"] += 1
        elif ot["estado"] not in ("cancelada",):
            semana_map[key]["pendientes"] += 1

    return {
        "ots_hoy": {
            "total": len([o for o in ots_hoy if o["estado"] != "cancelada"]),
            "en_curso": estados_hoy["en_curso"],
            "realizadas": estados_hoy["realizadas"],
            "pendientes": estados_hoy["pendientes"],
            "sin_asignar": sin_asignar,
        },
        "ots_ayer_total": ots_ayer_total,
        "semana": list(semana_map.values()),
        "tecnicos_hoy": list(tecnicos_map.values()),
    }
