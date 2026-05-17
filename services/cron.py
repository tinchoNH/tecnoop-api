from datetime import date, timedelta
from database import get_db
from routers.contratos import calcular_prox_ot


def generar_ots_manana() -> dict:
    """
    Genera OTs para mañana en todos los tenants.
    Se llama desde el endpoint /cron/generar-ots cada noche a las 20hs.
    """
    db = get_db()
    manana = (date.today() + timedelta(days=1)).isoformat()

    # Traer todos los contratos activos cuya prox_ot sea mañana
    contratos = (
        db.table("contratos")
        .select("*")
        .eq("activo", True)
        .eq("prox_ot", manana)
        .execute()
    ).data

    generadas = 0
    salteadas = 0
    errores = []

    for contrato in contratos:
        try:
            fecha_ot = contrato["prox_ot"]
            fecha_dt = date.fromisoformat(fecha_ot)

            # Si el contrato excluye fines de semana y mañana es sábado o domingo,
            # avanzar prox_ot sin generar OT
            if contrato.get("excluir_fines_semana") and fecha_dt.weekday() >= 5:
                dias_hasta_lunes = 7 - fecha_dt.weekday()
                sig = (fecha_dt + timedelta(days=dias_hasta_lunes)).isoformat()
                db.table("contratos").update({"prox_ot": sig}).eq("id", contrato["id"]).execute()
                salteadas += 1
                continue

            # Chequeo de duplicado: ya existe OT para este contrato en esta fecha?
            existe = (
                db.table("ordenes_trabajo")
                .select("id")
                .eq("contrato_id", contrato["id"])
                .eq("fecha_programada", fecha_ot)
                .execute()
            ).data

            if existe:
                salteadas += 1
                continue

            # Construir OT — estado pendiente, sin tipo_servicio específico
            # El admin lo completa antes de las 17hs del día anterior
            ot = {
                "empresa_id":      contrato["empresa_id"],
                "cliente_id":      contrato["cliente_id"],
                "contrato_id":     contrato["id"],
                "tipo_servicio":   contrato["tipo_servicio"],
                "fecha_programada": fecha_ot,
                "estado":          "pendiente",
                "descripcion":     "Generada automáticamente por contrato",
            }
            if contrato.get("sede_id"):
                ot["sede_id"] = contrato["sede_id"]
            if contrato.get("tecnico_id"):
                ot["tecnico_id"] = contrato["tecnico_id"]
                ot["estado"] = "asignada"
            if contrato.get("tecnicos_ids"):
                ot["tecnicos_ids"] = contrato["tecnicos_ids"]
                ot["tecnico_id"] = contrato["tecnicos_ids"][0]
                ot["estado"] = "asignada"

            db.table("ordenes_trabajo").insert(ot).execute()

            # Calcular siguiente prox_ot
            sig = calcular_prox_ot(
                contrato["frecuencia"],
                date.fromisoformat(fecha_ot) + timedelta(days=1),
                contrato.get("dia_semana"),
                contrato.get("dia_mes"),
            )
            db.table("contratos").update({"prox_ot": sig}).eq("id", contrato["id"]).execute()

            generadas += 1

        except Exception as e:
            errores.append({"contrato_id": contrato["id"], "error": str(e)})

    return {
        "fecha_generada": manana,
        "contratos_procesados": len(contratos),
        "ots_generadas": generadas,
        "salteadas": salteadas,
        "errores": errores,
    }
