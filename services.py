from typing import Tuple, Optional
from db import get_admin_status_by_id, count_admin_couriers, count_admin_couriers_with_min_balance


def admin_puede_operar(admin_id: int, min_couriers: int = 10, min_balance: int = 5000) -> Tuple[bool, str, int, int]:
    """
    Regla de negocio: un admin puede operar si:
    - existe y está APPROVED
    - tiene al menos `min_couriers` repartidores vinculados
    - y al menos `min_couriers` con balance >= `min_balance`

    Retorna:
    (puede_operar, motivo, total_couriers, couriers_ok_balance)
    """
    status = get_admin_status_by_id(admin_id)
    if not status:
        return False, "Administrador no encontrado.", 0, 0

    if status != "APPROVED":
        return False, f"Estado actual: {status}.", 0, 0

    total = count_admin_couriers(admin_id)
    ok = count_admin_couriers_with_min_balance(admin_id, min_balance=min_balance)

    if total < min_couriers:
        return False, f"No cumple mínimo de repartidores: {total}/{min_couriers}.", total, ok

    if ok < min_couriers:
        return False, f"No cumple saldo mínimo en repartidores: {ok}/{min_couriers} (>= {min_balance}).", total, ok

    return True, "OK", total, ok

