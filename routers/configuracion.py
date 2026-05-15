from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from auth import verify_token
from middleware.tenant import get_empresa_id
from database import get_db

router = APIRouter()

CONFIG_DEFAULT = {
    "usa_fotos":     False,
    "usa_firma":     True,
    "usa_productos": False,
    "usa_equipos":   False,
    "tipos_servicio": [],
}


class ConfigUpdate(BaseModel):
    usa_fotos:      Optional[bool] = None
    usa_firma:      Optional[bool] = None
    usa_productos:  Optional[bool] = None
    usa_equipos:    Optional[bool] = None
    tipos_servicio: Optional[list[str]] = None


class ProductoCreate(BaseModel):
    nombre: str
    unidad: str = "unidad"


class ProductoUpdate(BaseModel):
    nombre: Optional[str] = None
    unidad: Optional[str] = None
    activo: Optional[bool] = None


def solo_admin(token):
    if token.get("rol") not in ("admin", "superadmin"):
        raise HTTPException(403, "Se requiere rol admin")


# ─── Configuración general ───────────────────────────────────────────────────

@router.get("/")
def obtener_config(token=Depends(verify_token)):
    empresa_id = get_empresa_id(token)
    db = get_db()
    r = db.table("empresas").select("configuracion").eq("id", empresa_id).single().execute()
    config = r.data.get("configuracion") or {}
    # Merge con defaults para que no falten campos
    return {**CONFIG_DEFAULT, **config}


@router.put("/")
def actualizar_config(body: ConfigUpdate, token=Depends(verify_token)):
    solo_admin(token)
    empresa_id = get_empresa_id(token)
    db = get_db()

    r = db.table("empresas").select("configuracion").eq("id", empresa_id).single().execute()
    config_actual = r.data.get("configuracion") or {}
    config_actual = {**CONFIG_DEFAULT, **config_actual}

    nuevos = body.model_dump(exclude_none=True)
    config_actual.update(nuevos)

    db.table("empresas").update({"configuracion": config_actual}).eq("id", empresa_id).execute()
    return config_actual


# ─── Catálogo de productos ───────────────────────────────────────────────────

@router.get("/productos")
def listar_productos(token=Depends(verify_token)):
    empresa_id = get_empresa_id(token)
    db = get_db()
    r = (
        db.table("productos_catalogo")
        .select("*")
        .eq("empresa_id", empresa_id)
        .eq("activo", True)
        .order("nombre")
        .execute()
    )
    return r.data


@router.post("/productos")
def crear_producto(body: ProductoCreate, token=Depends(verify_token)):
    solo_admin(token)
    empresa_id = get_empresa_id(token)
    db = get_db()
    r = db.table("productos_catalogo").insert({
        "empresa_id": empresa_id,
        "nombre": body.nombre,
        "unidad": body.unidad,
    }).execute()
    return r.data[0]


@router.patch("/productos/{producto_id}")
def actualizar_producto(producto_id: str, body: ProductoUpdate, token=Depends(verify_token)):
    solo_admin(token)
    empresa_id = get_empresa_id(token)
    db = get_db()
    data = body.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(400, "Sin campos para actualizar")
    r = (
        db.table("productos_catalogo")
        .update(data)
        .eq("id", producto_id)
        .eq("empresa_id", empresa_id)
        .execute()
    )
    if not r.data:
        raise HTTPException(404, "Producto no encontrado")
    return r.data[0]


@router.delete("/productos/{producto_id}")
def eliminar_producto(producto_id: str, token=Depends(verify_token)):
    solo_admin(token)
    empresa_id = get_empresa_id(token)
    db = get_db()
    r = (
        db.table("productos_catalogo")
        .update({"activo": False})
        .eq("id", producto_id)
        .eq("empresa_id", empresa_id)
        .execute()
    )
    if not r.data:
        raise HTTPException(404, "Producto no encontrado")
    return {"ok": True}
