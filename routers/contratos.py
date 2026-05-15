from fastapi import APIRouter, Depends, HTTPException
from datetime import date, timedelta
import calendar
from auth import verify_token
from middleware.tenant import get_empresa_id
from database import get_db
from models.contratos import ContratoCreate, ContratoUpdate

router = APIRouter()

SELECT_COMPLETO = "*, clientes(id, razon_social), sedes(id, nombre, direccion), tecnicos(id, nombre)"

LABEL_FRECUENCIA = {
    "diaria": "Diaria",
    "semanal": "Semanal",
    "quincenal": "Quincenal",
    "mensual": "Mensual",
    "anual": "Anual",
}


def calcular_prox_ot(frecuencia: str, desde: date, dia_semana: int = None, dia_mes: int = None) -> str:
    hoy = date.today()
    base = max(desde, hoy)

    if frecuencia == "diaria":
        prox = base if base > hoy else hoy + timedelta(days=1)

    elif frecuencia == "semanal" and dia_semana is not None:
        dias = (dia_semana - base.weekday()) % 7
        prox = base + timedelta(days=dias if dias > 0 else 7)

    elif frecuencia == "quincenal":
        prox = base + timedelta(days=15)

    elif frecuencia == "mensual" and dia_mes is not None:
        # intentar en el mes actual
        try:
            candidato = base.replace(day=dia_mes)
        except ValueError:
            ultimo = calendar.monthrange(base.year, base.month)[1]
            candidato = base.replace(day=ultimo)
        if candidato <= hoy:
            # mover al mes siguiente
            if base.month == 12:
                sig = base.replace(year=base.year + 1, month=1, day=1)
            else:
                sig = base.replace(month=base.month + 1, day=1)
            try:
                candidato = sig.replace(day=dia_mes)
            except ValueError:
                candidato = sig.replace(day=calendar.monthrange(sig.year, sig.month)[1])
        prox = candidato

    elif frecuencia == "anual":
        try:
            prox = desde.replace(year=hoy.year + (1 if desde.replace(year=hoy.year) <= hoy else 0))
        except ValueError:
            prox = hoy + timedelta(days=365)

    else:
        prox = hoy + timedelta(days=1)

    return prox.isoformat()


def obtener_contrato(contrato_id: str, empresa_id: str, db):
    r = (
        db.table("contratos")
        .select(SELECT_COMPLETO)
        .eq("id", contrato_id)
        .eq("empresa_id", empresa_id)
        .single()
        .execute()
    )
    if not r.data:
        raise HTTPException(404, "Contrato no encontrado")
    return r.data


@router.get("/")
def listar_contratos(activo: bool = None, cliente_id: str = None, token=Depends(verify_token)):
    empresa_id = get_empresa_id(token)
    db = get_db()
    q = db.table("contratos").select(SELECT_COMPLETO).eq("empresa_id", empresa_id)
    if activo is not None:
        q = q.eq("activo", activo)
    if cliente_id:
        q = q.eq("cliente_id", cliente_id)
    r = q.order("created_at", desc=True).execute()
    return r.data


@router.get("/{contrato_id}")
def obtener(contrato_id: str, token=Depends(verify_token)):
    empresa_id = get_empresa_id(token)
    return obtener_contrato(contrato_id, empresa_id, get_db())


@router.post("/")
def crear_contrato(body: ContratoCreate, token=Depends(verify_token)):
    empresa_id = get_empresa_id(token)
    db = get_db()
    data = body.model_dump(exclude_none=True)
    data["empresa_id"] = empresa_id
    data["activo"] = True
    data["inicio"] = str(data["inicio"])
    if "fin" in data:
        data["fin"] = str(data["fin"])
    data["prox_ot"] = calcular_prox_ot(
        data["frecuencia"],
        body.inicio,
        data.get("dia_semana"),
        data.get("dia_mes"),
    )
    r = db.table("contratos").insert(data).execute()
    return obtener_contrato(r.data[0]["id"], empresa_id, db)


@router.patch("/{contrato_id}")
def actualizar_contrato(contrato_id: str, body: ContratoUpdate, token=Depends(verify_token)):
    empresa_id = get_empresa_id(token)
    db = get_db()
    data = body.model_dump(exclude_none=True)
    if "fin" in data:
        data["fin"] = str(data["fin"])
    if not data:
        raise HTTPException(400, "Sin campos para actualizar")
    r = db.table("contratos").update(data).eq("id", contrato_id).eq("empresa_id", empresa_id).execute()
    if not r.data:
        raise HTTPException(404, "Contrato no encontrado")
    return obtener_contrato(contrato_id, empresa_id, db)


@router.delete("/{contrato_id}")
def desactivar_contrato(contrato_id: str, token=Depends(verify_token)):
    empresa_id = get_empresa_id(token)
    db = get_db()
    r = db.table("contratos").update({"activo": False}).eq("id", contrato_id).eq("empresa_id", empresa_id).execute()
    if not r.data:
        raise HTTPException(404, "Contrato no encontrado")
    return {"ok": True}


@router.post("/{contrato_id}/generar-ot")
def generar_ot(contrato_id: str, token=Depends(verify_token)):
    empresa_id = get_empresa_id(token)
    db = get_db()
    contrato = obtener_contrato(contrato_id, empresa_id, db)

    if not contrato["activo"]:
        raise HTTPException(400, "El contrato está inactivo")

    ot = {
        "empresa_id": empresa_id,
        "cliente_id": contrato["cliente_id"],
        "sede_id": contrato["sede_id"],
        "contrato_id": contrato_id,
        "tipo_servicio": contrato["tipo_servicio"],
        "descripcion": f"OT generada por contrato {LABEL_FRECUENCIA.get(contrato['frecuencia'], contrato['frecuencia']).lower()}",
        "fecha_programada": contrato["prox_ot"],
        "estado": "asignada" if contrato.get("tecnico_id") else "pendiente",
    }
    if contrato.get("tecnico_id"):
        ot["tecnico_id"] = contrato["tecnico_id"]

    db.table("ordenes_trabajo").insert(ot).execute()

    # Calcular y guardar la siguiente prox_ot
    sig = calcular_prox_ot(
        contrato["frecuencia"],
        date.fromisoformat(contrato["prox_ot"]) + timedelta(days=1),
        contrato.get("dia_semana"),
        contrato.get("dia_mes"),
    )
    db.table("contratos").update({"prox_ot": sig}).eq("id", contrato_id).execute()

    return {"ok": True, "ot_fecha": ot["fecha_programada"], "prox_ot": sig}
