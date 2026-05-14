from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from auth import verify_token
from middleware.tenant import get_empresa_id
from database import get_db
from models.ordenes import OrdenCreate, OrdenUpdate, ESTADOS_VALIDOS

router = APIRouter()


@router.get("/")
def listar_ordenes(fecha: str = None, estado: str = None, tecnico_id: str = None, token=Depends(verify_token)):
    empresa_id = get_empresa_id(token)
    db = get_db()
    query = db.table("ordenes_trabajo").select("*, tecnicos(nombre), clientes(razon_social), sedes(nombre, direccion)") \
              .eq("empresa_id", empresa_id)
    if fecha:
        query = query.eq("fecha_programada", fecha)
    if estado:
        query = query.eq("estado", estado)
    if tecnico_id:
        query = query.eq("tecnico_id", tecnico_id)
    result = query.order("fecha_programada", desc=True).execute()
    return result.data


@router.get("/{orden_id}")
def obtener_orden(orden_id: str, token=Depends(verify_token)):
    empresa_id = get_empresa_id(token)
    db = get_db()
    result = db.table("ordenes_trabajo").select("*").eq("id", orden_id).eq("empresa_id", empresa_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    return result.data[0]


@router.post("/")
def crear_orden(body: OrdenCreate, token=Depends(verify_token)):
    empresa_id = get_empresa_id(token)
    db = get_db()
    data = body.dict()
    data["empresa_id"] = empresa_id
    data["fecha_programada"] = str(data["fecha_programada"])
    data["estado"] = "asignada" if data.get("tecnico_id") else "pendiente"
    result = db.table("ordenes_trabajo").insert(data).execute()
    return result.data[0]


@router.patch("/{orden_id}/estado")
def cambiar_estado(orden_id: str, nuevo_estado: str, token=Depends(verify_token)):
    empresa_id = get_empresa_id(token)
    db = get_db()

    orden = db.table("ordenes_trabajo").select("estado").eq("id", orden_id).eq("empresa_id", empresa_id).execute()
    if not orden.data:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    estado_actual = orden.data[0]["estado"]
    if nuevo_estado not in ESTADOS_VALIDOS.get(estado_actual, []):
        raise HTTPException(status_code=400, detail=f"Transición inválida: {estado_actual} → {nuevo_estado}")

    update_data = {"estado": nuevo_estado}
    if nuevo_estado == "en_curso":
        update_data["fecha_inicio_real"] = datetime.utcnow().isoformat()
    elif nuevo_estado == "realizada":
        update_data["fecha_cierre_real"] = datetime.utcnow().isoformat()

    result = db.table("ordenes_trabajo").update(update_data).eq("id", orden_id).eq("empresa_id", empresa_id).execute()
    return result.data[0]


@router.patch("/{orden_id}")
def actualizar_orden(orden_id: str, body: OrdenUpdate, token=Depends(verify_token)):
    empresa_id = get_empresa_id(token)
    db = get_db()
    data = {k: v for k, v in body.dict().items() if v is not None}
    result = db.table("ordenes_trabajo").update(data).eq("id", orden_id).eq("empresa_id", empresa_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    return result.data[0]
