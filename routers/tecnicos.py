from fastapi import APIRouter, Depends, HTTPException
from auth import verify_token
from middleware.tenant import get_empresa_id
from database import get_db
from models.tecnicos import TecnicoCreate, TecnicoUpdate

router = APIRouter()


@router.get("/")
def listar_tecnicos(token=Depends(verify_token)):
    empresa_id = get_empresa_id(token)
    db = get_db()
    result = db.table("tecnicos").select("*").eq("empresa_id", empresa_id).eq("activo", True).execute()
    return result.data


@router.get("/{tecnico_id}")
def obtener_tecnico(tecnico_id: str, token=Depends(verify_token)):
    empresa_id = get_empresa_id(token)
    db = get_db()
    result = db.table("tecnicos").select("*").eq("id", tecnico_id).eq("empresa_id", empresa_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Técnico no encontrado")
    return result.data[0]


@router.post("/")
def crear_tecnico(body: TecnicoCreate, token=Depends(verify_token)):
    empresa_id = get_empresa_id(token)
    db = get_db()
    data = body.dict()
    data["empresa_id"] = empresa_id
    if data.get("ingreso"):
        data["ingreso"] = str(data["ingreso"])
    result = db.table("tecnicos").insert(data).execute()
    return result.data[0]


@router.patch("/{tecnico_id}")
def actualizar_tecnico(tecnico_id: str, body: TecnicoUpdate, token=Depends(verify_token)):
    empresa_id = get_empresa_id(token)
    db = get_db()
    data = {k: v for k, v in body.dict().items() if v is not None}
    result = db.table("tecnicos").update(data).eq("id", tecnico_id).eq("empresa_id", empresa_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Técnico no encontrado")
    return result.data[0]


@router.delete("/{tecnico_id}")
def eliminar_tecnico(tecnico_id: str, token=Depends(verify_token)):
    empresa_id = get_empresa_id(token)
    db = get_db()
    # Soft delete
    db.table("tecnicos").update({"activo": False}).eq("id", tecnico_id).eq("empresa_id", empresa_id).execute()
    return {"ok": True}


@router.patch("/{tecnico_id}/ubicacion")
def actualizar_ubicacion(tecnico_id: str, lat: float, lng: float, token=Depends(verify_token)):
    """Llamado desde la app móvil del técnico para actualizar su posición GPS."""
    empresa_id = get_empresa_id(token)
    db = get_db()
    db.table("tecnicos").update({"lat": lat, "lng": lng}).eq("id", tecnico_id).eq("empresa_id", empresa_id).execute()
    return {"ok": True}
