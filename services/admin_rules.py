# services/admin_rules.py

from db import get_admin_by_id, count_admin_couriers, count_admin_couriers_with_min_balance


def admin_puede_operar(admin_id: int):
    """
    Aprobación != operación.
    Operación solo si cumple requisitos en tiempo real.
    Retorna (True, None) o (False, mensaje).
    """
    admin = get_admin_by_id(admin_id)
    if not admin:
        return (False, "No se pudo validar tu cuenta de administrador.")

    # Soportar dict o tupla (mientras normalizas db.py)
    status = admin["status"] if isinstance(admin, dict) else admin[6]

    if status != "APPROVED":
        return (False, f"Tu cuenta no está habilitada. Estado actual: {status}")

    total = count_admin_couriers(admin_id)
    ok = count_admin_couriers_with_min_balance(admin_id, 5000)

    if total < 10 or ok < 10:
        msg = (
            "Aún no puedes operar como Administrador Local.\n\n"
            "Requisitos para operar:\n"
            "1) 10 repartidores vinculados a tu equipo\n"
            "2) Los 10 deben estar APROBADOS\n"
            "3) Cada uno con saldo por vínculo >= 5000\n\n"
            f"Tu estado actual:\n"
            f"- Vinculados: {total}\n"
            f"- Con saldo >= 5000: {ok}\n\n"
            "Acción: completa vínculos y recargas. Cuando cumplas, el sistema te habilita automáticamente."
        )
        return (False, msg)

    return (True, None)
