from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, date
from auth import verify_token
from middleware.tenant import get_empresa_id
from database import get_db
from models.ordenes import OrdenCreate, OrdenUpdate, CambioEstado, ESTADOS_VALIDOS

router = APIRouter()

SELECT_COMPLETO = "*, tecnicos(id, nombre, estado), clientes(id, razon_social), sedes(id, nombre, direccion)"


@router.get("/")
def listar_ordenes(
    fecha: str = None,
    estado: str = None,
    tecnico_id: str = None,
    desde: str = None,
    hasta: str = None,
    token=Depends(verify_token),
):
    empresa_id = get_empresa_id(token)
    db = get_db()
    query = (
        db.table("ordenes_trabajo")
        .select(SELECT_COMPLETO)
        .eq("empresa_id", empresa_id)
    )
    if fecha:
        query = query.eq("fecha_programada", fecha)
    if estado:
        query = query.eq("estado", estado)
    if tecnico_id:
        query = query.eq("tecnico_id", tecnico_id)
    if desde:
        query = query.gte("fecha_programada", desde)
    if hasta:
        query = query.lte("fecha_programada", hasta)
    result = query.order("fecha_programada", desc=True).order("hora_inicio").execute()
    return result.data


@router.get("/mis-ots")
def mis_ordenes_hoy(token=Depends(verify_token)):
    empresa_id = get_empresa_id(token)
    tecnico_id = token.get("tecnico_id")
    if not tecnico_id:
        raise HTTPException(403, "Este endpoint es solo para técnicos")
    db = get_db()
    hoy = date.today().isoformat()
    result = (
        db.table("ordenes_trabajo")
        .select(SELECT_COMPLETO)
        .eq("empresa_id", empresa_id)
        .eq("fecha_programada", hoy)
        .order("hora_inicio")
        .execute()
    )
    # Filtrar en Python para cubrir tecnico_id legacy y tecnicos_ids array
    data = [
        o for o in result.data
        if o.get("tecnico_id") == tecnico_id
        or tecnico_id in (o.get("tecnicos_ids") or [])
    ]
    return data


@router.get("/hoy")
def ordenes_hoy(token=Depends(verify_token)):
    empresa_id = get_empresa_id(token)
    db = get_db()
    hoy = date.today().isoformat()
    result = (
        db.table("ordenes_trabajo")
        .select(SELECT_COMPLETO)
        .eq("empresa_id", empresa_id)
        .eq("fecha_programada", hoy)
        .order("hora_inicio")
        .execute()
    )
    return result.data


@router.get("/{orden_id}")
def obtener_orden(orden_id: str, token=Depends(verify_token)):
    empresa_id = get_empresa_id(token)
    db = get_db()
    result = (
        db.table("ordenes_trabajo")
        .select(SELECT_COMPLETO)
        .eq("id", orden_id)
        .eq("empresa_id", empresa_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Orden no encontrada")
    return result.data


@router.post("/")
def crear_orden(body: OrdenCreate, token=Depends(verify_token)):
    empresa_id = get_empresa_id(token)
    db = get_db()
    data = body.model_dump(exclude_none=True)
    data["empresa_id"] = empresa_id
    data["fecha_programada"] = str(data["fecha_programada"])
    # Sincronizar tecnico_id <-> tecnicos_ids
    if data.get("tecnicos_ids"):
        data["tecnico_id"] = data["tecnicos_ids"][0]
    elif data.get("tecnico_id"):
        data["tecnicos_ids"] = [data["tecnico_id"]]
    data["estado"] = "asignada" if data.get("tecnico_id") else "pendiente"
    result = db.table("ordenes_trabajo").insert(data).execute()
    return obtener_orden(result.data[0]["id"], token)


@router.patch("/{orden_id}")
def actualizar_orden(orden_id: str, body: OrdenUpdate, token=Depends(verify_token)):
    empresa_id = get_empresa_id(token)
    db = get_db()
    data = body.model_dump(exclude_none=True)
    if "fecha_programada" in data:
        data["fecha_programada"] = str(data["fecha_programada"])
    # Sincronizar tecnico_id <-> tecnicos_ids
    if data.get("tecnicos_ids"):
        data["tecnico_id"] = data["tecnicos_ids"][0]
    elif data.get("tecnico_id"):
        data["tecnicos_ids"] = [data["tecnico_id"]]
    # Si hay técnico y la orden está pendiente, pasarla a asignada
    if data.get("tecnico_id"):
        orden = db.table("ordenes_trabajo").select("estado").eq("id", orden_id).eq("empresa_id", empresa_id).single().execute()
        if orden.data and orden.data["estado"] == "pendiente":
            data["estado"] = "asignada"
    result = db.table("ordenes_trabajo").update(data).eq("id", orden_id).eq("empresa_id", empresa_id).execute()
    if not result.data:
        raise HTTPException(404, "Orden no encontrada")
    return obtener_orden(orden_id, token)


@router.patch("/{orden_id}/estado")
def cambiar_estado(orden_id: str, body: CambioEstado, token=Depends(verify_token)):
    empresa_id = get_empresa_id(token)
    db = get_db()
    orden = (
        db.table("ordenes_trabajo")
        .select("estado")
        .eq("id", orden_id)
        .eq("empresa_id", empresa_id)
        .single()
        .execute()
    )
    if not orden.data:
        raise HTTPException(404, "Orden no encontrada")
    estado_actual = orden.data["estado"]
    nuevo = body.estado
    if nuevo not in ESTADOS_VALIDOS.get(estado_actual, []):
        raise HTTPException(400, f"Transición inválida: {estado_actual} → {nuevo}")
    update = {"estado": nuevo}
    if nuevo == "en_curso":
        update["fecha_inicio_real"] = datetime.utcnow().isoformat()
    elif nuevo == "realizada":
        update["fecha_cierre_real"] = datetime.utcnow().isoformat()
    db.table("ordenes_trabajo").update(update).eq("id", orden_id).execute()
    return obtener_orden(orden_id, token)


@router.delete("/{orden_id}")
def cancelar_orden(orden_id: str, token=Depends(verify_token)):
    empresa_id = get_empresa_id(token)
    db = get_db()
    orden = db.table("ordenes_trabajo").select("estado").eq("id", orden_id).eq("empresa_id", empresa_id).single().execute()
    if not orden.data:
        raise HTTPException(404, "Orden no encontrada")
    if orden.data["estado"] == "realizada":
        raise HTTPException(400, "No se puede cancelar una orden ya realizada")
    db.table("ordenes_trabajo").update({"estado": "cancelada"}).eq("id", orden_id).execute()
    return {"ok": True}
