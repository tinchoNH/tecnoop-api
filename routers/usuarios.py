from fastapi import APIRouter, Depends, HTTPException
import bcrypt
from auth import verify_token
from middleware.tenant import get_empresa_id
from database import get_db
from models.usuarios import UsuarioCreate, UsuarioUpdate

router = APIRouter()

ROLES_PERMITIDOS = {"admin", "supervisor", "tecnico", "cliente"}

SELECT_COMPLETO = "id, nombre, email, rol, tecnico_id, activo, created_at, tecnicos(id, nombre)"


def solo_admin(token):
    if token.get("rol") not in ("admin", "superadmin"):
        raise HTTPException(403, "Se requiere rol admin")


def obtener_usuario(usuario_id: str, empresa_id: str, db):
    r = (
        db.table("usuarios")
        .select(SELECT_COMPLETO)
        .eq("id", usuario_id)
        .eq("empresa_id", empresa_id)
        .single()
        .execute()
    )
    if not r.data:
        raise HTTPException(404, "Usuario no encontrado")
    return r.data


@router.get("/")
def listar_usuarios(token=Depends(verify_token)):
    solo_admin(token)
    empresa_id = get_empresa_id(token)
    db = get_db()
    r = (
        db.table("usuarios")
        .select(SELECT_COMPLETO)
        .eq("empresa_id", empresa_id)
        .order("nombre")
        .execute()
    )
    return r.data


@router.post("/")
def crear_usuario(body: UsuarioCreate, token=Depends(verify_token)):
    solo_admin(token)
    empresa_id = get_empresa_id(token)
    db = get_db()

    if body.rol not in ROLES_PERMITIDOS:
        raise HTTPException(400, f"Rol inválido. Opciones: {', '.join(ROLES_PERMITIDOS)}")

    # Verificar email único
    existe = db.table("usuarios").select("id").eq("email", body.email).execute()
    if existe.data:
        raise HTTPException(400, "Ya existe un usuario con ese email")

    hashed = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()

    data = {
        "empresa_id": empresa_id,
        "nombre": body.nombre,
        "email": body.email,
        "password": hashed,
        "rol": body.rol,
        "activo": True,
    }
    if body.tecnico_id:
        data["tecnico_id"] = body.tecnico_id

    r = db.table("usuarios").insert(data).execute()
    return obtener_usuario(r.data[0]["id"], empresa_id, db)


@router.patch("/{usuario_id}")
def actualizar_usuario(usuario_id: str, body: UsuarioUpdate, token=Depends(verify_token)):
    solo_admin(token)
    empresa_id = get_empresa_id(token)
    db = get_db()

    data = body.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(400, "Sin campos para actualizar")

    if "rol" in data and data["rol"] not in ROLES_PERMITIDOS:
        raise HTTPException(400, f"Rol inválido. Opciones: {', '.join(ROLES_PERMITIDOS)}")

    r = db.table("usuarios").update(data).eq("id", usuario_id).eq("empresa_id", empresa_id).execute()
    if not r.data:
        raise HTTPException(404, "Usuario no encontrado")
    return obtener_usuario(usuario_id, empresa_id, db)


@router.delete("/{usuario_id}")
def desactivar_usuario(usuario_id: str, token=Depends(verify_token)):
    solo_admin(token)
    empresa_id = get_empresa_id(token)

    if token.get("user_id") == usuario_id:
        raise HTTPException(400, "No podés desactivar tu propio usuario")

    db = get_db()
    r = db.table("usuarios").update({"activo": False}).eq("id", usuario_id).eq("empresa_id", empresa_id).execute()
    if not r.data:
        raise HTTPException(404, "Usuario no encontrado")
    return {"ok": True}
