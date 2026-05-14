from fastapi import HTTPException
from auth import verify_token


def get_empresa_id(token_data: dict) -> str:
    """Extrae y valida empresa_id del JWT. Usar como dependency en todos los routers."""
    empresa_id = token_data.get("empresa_id")
    if not empresa_id:
        raise HTTPException(status_code=403, detail="empresa_id no encontrado en el token")
    return empresa_id
