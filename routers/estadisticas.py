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

    r_hoy = (
        db.table("ordenes_trabajo")
        .select("id, estado, tecnico_id, tecnicos(id, nombre, estado)")
        .eq("empresa_id", empresa_id)
        .eq("fecha_programada", hoy.isoformat())
        .execute()
    )
    ots_hoy = r_hoy.data or []

    estados_hoy = {"en_curso": 0, "realizadas": 0, "pendientes": 0}
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

        if not ot.get("tecnico_id"):
            sin_asignar += 1

        tec = ot.get("tecnicos")
        if tec:
            tid = tec["id"]
            if tid not in tecnicos_map:
                tecnicos_map[tid] = {"nombre": tec["nombre"], "estado": tec["estado"], "realizadas": 0, "total": 0}
            tecnicos_map[tid]["total"] += 1
            if estado == "realizada":
                tecnicos_map[tid]["realizadas"] += 1

    r_ayer = (
        db.table("ordenes_trabajo")
        .select("id", count="exact")
        .eq("empresa_id", empresa_id)
        .eq("fecha_programada", ayer.isoformat())
        .neq("estado", "cancelada")
        .execute()
    )
    ots_ayer_total = r_ayer.count if r_ayer.count is not None else len(r_ayer.data or [])

    desde = (hoy - timedelta(days=6)).isoformat()
    r_semana = (
        db.table("ordenes_trabajo")
        .select("fecha_programada, estado")
        .eq("empresa_id", empresa_id)
        .gte("fecha_programada", desde)
        .lte("fecha_programada", hoy.isoformat())
        .execute()
    )

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
        elif ot["estado"] != "cancelada":
            semana_map[key]["pendientes"] += 1

    # OTs pendientes hoy (para dashboard)
    r_pendientes = (
        db.table("ordenes_trabajo")
        .select("id, tipo_servicio, hora_inicio, estado, clientes(razon_social)")
        .eq("empresa_id", empresa_id)
        .eq("fecha_programada", hoy.isoformat())
        .in_("estado", ["pendiente", "asignada", "en_curso"])
        .order("hora_inicio")
        .limit(10)
        .execute()
    )
    ots_pendientes_hoy = r_pendientes.data or []

    # Próximas OTs de contratos activos
    r_contratos = (
        db.table("contratos")
        .select("id, tipo_servicio, prox_ot, clientes(razon_social)")
        .eq("empresa_id", empresa_id)
        .eq("activo", True)
        .order("prox_ot")
        .limit(5)
        .execute()
    )
    proximas_contratos = r_contratos.data or []

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
        "ots_pendientes_hoy": ots_pendientes_hoy,
        "proximas_contratos": proximas_contratos,
    }


@router.get("/resumen")
def resumen(desde: str = None, hasta: str = None, token=Depends(verify_token)):
    empresa_id = get_empresa_id(token)
    db = get_db()

    hoy = date.today()
    fecha_hasta = date.fromisoformat(hasta) if hasta else hoy
    fecha_desde = date.fromisoformat(desde) if desde else hoy.replace(day=1)

    r = (
        db.table("ordenes_trabajo")
        .select("id, estado, fecha_programada, tipo_servicio, tecnico_id, tecnicos(id, nombre)")
        .eq("empresa_id", empresa_id)
        .gte("fecha_programada", fecha_desde.isoformat())
        .lte("fecha_programada", fecha_hasta.isoformat())
        .execute()
    )
    ots = r.data or []

    # KPIs globales
    total = len(ots)
    realizadas = sum(1 for o in ots if o["estado"] == "realizada")
    canceladas = sum(1 for o in ots if o["estado"] == "cancelada")
    pendientes = sum(1 for o in ots if o["estado"] in ("pendiente", "asignada", "en_curso"))
    cumplimiento = round((realizadas / total * 100) if total > 0 else 0)

    # Por día
    dias_map: dict[str, dict] = {}
    delta = (fecha_hasta - fecha_desde).days + 1
    for i in range(delta):
        d = fecha_desde + timedelta(days=i)
        key = d.isoformat()
        label = d.strftime("%-d/%m") if hasattr(d, "strftime") else key
        # Windows-safe strftime
        try:
            label = d.strftime("%-d/%m")
        except ValueError:
            label = d.strftime("%d/%m").lstrip("0") or "0"
        dias_map[key] = {"dia": key, "realizadas": 0, "pendientes": 0, "canceladas": 0}

    for ot in ots:
        key = ot["fecha_programada"]
        if key not in dias_map:
            continue
        e = ot["estado"]
        if e == "realizada":
            dias_map[key]["realizadas"] += 1
        elif e == "cancelada":
            dias_map[key]["canceladas"] += 1
        else:
            dias_map[key]["pendientes"] += 1

    # Ranking de técnicos
    tec_map: dict[str, dict] = {}
    for ot in ots:
        if ot["estado"] == "cancelada":
            continue
        tec = ot.get("tecnicos")
        if not tec:
            continue
        tid = tec["id"]
        if tid not in tec_map:
            tec_map[tid] = {"nombre": tec["nombre"], "realizadas": 0, "total": 0}
        tec_map[tid]["total"] += 1
        if ot["estado"] == "realizada":
            tec_map[tid]["realizadas"] += 1

    ranking = sorted(tec_map.values(), key=lambda x: x["realizadas"], reverse=True)
    for t in ranking:
        t["pct"] = round(t["realizadas"] / t["total"] * 100) if t["total"] > 0 else 0

    # Distribución por tipo de servicio
    tipo_map: dict[str, int] = {}
    for ot in ots:
        if ot["estado"] == "cancelada":
            continue
        tipo = ot.get("tipo_servicio") or "Sin especificar"
        tipo_map[tipo] = tipo_map.get(tipo, 0) + 1

    tipos = [{"tipo": k, "cantidad": v} for k, v in sorted(tipo_map.items(), key=lambda x: x[1], reverse=True)]

    return {
        "periodo": {"desde": fecha_desde.isoformat(), "hasta": fecha_hasta.isoformat()},
        "kpis": {
            "total": total,
            "realizadas": realizadas,
            "canceladas": canceladas,
            "pendientes": pendientes,
            "cumplimiento": cumplimiento,
        },
        "por_dia": list(dias_map.values()),
        "ranking_tecnicos": ranking,
        "por_tipo": tipos,
    }


@router.get("/horas-tecnicos")
def horas_tecnicos(desde: str = None, hasta: str = None, token=Depends(verify_token)):
    """
    Devuelve horas trabajadas vs esperadas por técnico en el período.
    Las horas trabajadas se estiman como: OTs realizadas × horas_base del técnico.
    Las horas esperadas se calculan como: días hábiles × horas_base.
    """
    empresa_id = get_empresa_id(token)
    db = get_db()

    hoy = date.today()
    fecha_hasta = date.fromisoformat(hasta) if hasta else hoy
    fecha_desde = date.fromisoformat(desde) if desde else hoy - timedelta(days=6)

    # Días hábiles (lunes-viernes) en el período
    dias_habiles = sum(
        1 for i in range((fecha_hasta - fecha_desde).days + 1)
        if (fecha_desde + timedelta(days=i)).weekday() < 5
    )

    # Técnicos activos
    r_tecs = (
        db.table("tecnicos")
        .select("id, nombre, horas_base, estado")
        .eq("empresa_id", empresa_id)
        .execute()
    )
    tecnicos = {t["id"]: t for t in (r_tecs.data or [])}

    # OTs realizadas en el período
    r_ots = (
        db.table("ordenes_trabajo")
        .select("tecnico_id, tecnicos_ids, estado, fecha_programada")
        .eq("empresa_id", empresa_id)
        .eq("estado", "realizada")
        .gte("fecha_programada", fecha_desde.isoformat())
        .lte("fecha_programada", fecha_hasta.isoformat())
        .execute()
    )
    ots = r_ots.data or []

    # Contar OTs por técnico
    ots_por_tec: dict[str, int] = {}
    for ot in ots:
        ids = ot.get("tecnicos_ids") or ([ot["tecnico_id"]] if ot.get("tecnico_id") else [])
        for tid in ids:
            ots_por_tec[tid] = ots_por_tec.get(tid, 0) + 1

    resultado = []
    for tid, tec in tecnicos.items():
        horas_base   = tec.get("horas_base") or 8
        ots_realizadas = ots_por_tec.get(tid, 0)
        horas_trabajadas = ots_realizadas * horas_base  # estimación: 1 OT = horas_base
        horas_esperadas  = dias_habiles * horas_base
        diferencia       = horas_trabajadas - horas_esperadas
        resultado.append({
            "id":               tid,
            "nombre":           tec["nombre"],
            "estado":           tec["estado"],
            "horas_base":       horas_base,
            "horas_esperadas":  horas_esperadas,
            "horas_trabajadas": horas_trabajadas,
            "ots_realizadas":   ots_realizadas,
            "diferencia":       diferencia,          # positivo = horas extra, negativo = faltante
            "cumplimiento_pct": round(min((horas_trabajadas / horas_esperadas * 100), 150)) if horas_esperadas > 0 else 0,
        })

    resultado.sort(key=lambda x: x["horas_trabajadas"], reverse=True)

    return {
        "periodo": {"desde": fecha_desde.isoformat(), "hasta": fecha_hasta.isoformat(), "dias_habiles": dias_habiles},
        "tecnicos": resultado,
    }
