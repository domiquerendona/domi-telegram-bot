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


def calcular_precio_por_distancia(
    distancia_km: float,
    precio_hasta_2km: int = 5000,
    precio_2_a_3km: int = 6000,
    precio_base_mas_3km: int = 6000,
    precio_por_km_adicional: int = 1200
) -> int:
    """
    Calcula el precio de envío basado en la distancia.

    Reglas:
    - 0-2 km: precio_hasta_2km
    - 2.1-3 km: precio_2_a_3km
    - >3 km: precio_base_mas_3km + (km completos adicionales * precio_por_km_adicional)

    Args:
        distancia_km: Distancia en kilómetros
        precio_hasta_2km: Precio para distancias de 0 a 2 km (por defecto 5000)
        precio_2_a_3km: Precio para distancias de 2.1 a 3 km (por defecto 6000)
        precio_base_mas_3km: Precio base para distancias mayores a 3 km (por defecto 6000)
        precio_por_km_adicional: Precio por cada km adicional después de 3 km (por defecto 1200)

    Returns:
        Precio calculado en pesos

    Ejemplos:
        >>> calcular_precio_por_distancia(1.5)
        5000
        >>> calcular_precio_por_distancia(2.5)
        6000
        >>> calcular_precio_por_distancia(4.8)
        7200  # 6000 + (1 * 1200)
        >>> calcular_precio_por_distancia(6.2)
        9600  # 6000 + (3 * 1200)
    """
    if distancia_km <= 2.0:
        return precio_hasta_2km
    elif distancia_km <= 3.0:
        return precio_2_a_3km
    else:
        # km adicionales sobre 3 km, redondeados hacia abajo
        km_adicionales = int(distancia_km - 3.0)
        return precio_base_mas_3km + (km_adicionales * precio_por_km_adicional)

