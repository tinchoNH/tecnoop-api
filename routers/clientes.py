from fastapi import APIRouter, Depends, HTTPException
from auth import verify_token
from middleware.tenant import get_empresa_id
from database import get_db
from models.clientes import ClienteCreate, ClienteUpdate, SedeCreate, SedeUpdate

router = APIRouter()


# ── Clientes ──────────────────────────────────────────────

@router.get("/")
async def listar_clientes(token_data=Depends(verify_token)):
    empresa_id = get_empresa_id(token_data)
    db = get_db()
    res = (
        db.table("clientes")
        .select("*")
        .eq("empresa_id", empresa_id)
        .eq("activo", True)
        .order("razon_social")
        .execute()
    )
    return res.data


@router.get("/{cliente_id}")
async def obtener_cliente(cliente_id: str, token_data=Depends(verify_token)):
    empresa_id = get_empresa_id(token_data)
    db = get_db()
    res = (
        db.table("clientes")
        .select("*")
        .eq("id", cliente_id)
        .eq("empresa_id", empresa_id)
        .single()
        .execute()
    )
    if not res.data:
        raise HTTPException(404, "Cliente no encontrado")
    return res.data


@router.post("/")
async def crear_cliente(body: ClienteCreate, token_data=Depends(verify_token)):
    empresa_id = get_empresa_id(token_data)
    db = get_db()
    data = body.model_dump(exclude_none=True)
    data["empresa_id"] = empresa_id
    res = db.table("clientes").insert(data).execute()
    return res.data[0]


@router.patch("/{cliente_id}")
async def actualizar_cliente(cliente_id: str, body: ClienteUpdate, token_data=Depends(verify_token)):
    empresa_id = get_empresa_id(token_data)
    db = get_db()
    # verify ownership
    check = (
        db.table("clientes")
        .select("id")
        .eq("id", cliente_id)
        .eq("empresa_id", empresa_id)
        .execute()
    )
    if not check.data:
        raise HTTPException(404, "Cliente no encontrado")
    data = body.model_dump(exclude_none=True)
    res = db.table("clientes").update(data).eq("id", cliente_id).execute()
    return res.data[0]


@router.delete("/{cliente_id}")
async def eliminar_cliente(cliente_id: str, token_data=Depends(verify_token)):
    empresa_id = get_empresa_id(token_data)
    db = get_db()
    check = (
        db.table("clientes")
        .select("id")
        .eq("id", cliente_id)
        .eq("empresa_id", empresa_id)
        .execute()
    )
    if not check.data:
        raise HTTPException(404, "Cliente no encontrado")
    db.table("clientes").update({"activo": False}).eq("id", cliente_id).execute()
    return {"ok": True}


# ── Sedes ─────────────────────────────────────────────────

@router.get("/{cliente_id}/sedes")
async def listar_sedes(cliente_id: str, token_data=Depends(verify_token)):
    empresa_id = get_empresa_id(token_data)
    db = get_db()
    res = (
        db.table("sedes")
        .select("*")
        .eq("cliente_id", cliente_id)
        .eq("empresa_id", empresa_id)
        .order("nombre")
        .execute()
    )
    return res.data


@router.post("/{cliente_id}/sedes")
async def crear_sede(cliente_id: str, body: SedeCreate, token_data=Depends(verify_token)):
    empresa_id = get_empresa_id(token_data)
    db = get_db()
    data = body.model_dump(exclude_none=True)
    data["cliente_id"] = cliente_id
    data["empresa_id"] = empresa_id
    res = db.table("sedes").insert(data).execute()
    return res.data[0]


@router.patch("/sedes/{sede_id}")
async def actualizar_sede(sede_id: str, body: SedeUpdate, token_data=Depends(verify_token)):
    empresa_id = get_empresa_id(token_data)
    db = get_db()
    check = (
        db.table("sedes")
        .select("id")
        .eq("id", sede_id)
        .eq("empresa_id", empresa_id)
        .execute()
    )
    if not check.data:
        raise HTTPException(404, "Sede no encontrada")
    data = body.model_dump(exclude_none=True)
    res = db.table("sedes").update(data).eq("id", sede_id).execute()
    return res.data[0]


@router.delete("/sedes/{sede_id}")
async def eliminar_sede(sede_id: str, token_data=Depends(verify_token)):
    empresa_id = get_empresa_id(token_data)
    db = get_db()
    check = (
        db.table("sedes")
        .select("id")
        .eq("id", sede_id)
        .eq("empresa_id", empresa_id)
        .execute()
    )
    if not check.data:
        raise HTTPException(404, "Sede no encontrada")
    db.table("sedes").delete().eq("id", sede_id).execute()
    return {"ok": True}
