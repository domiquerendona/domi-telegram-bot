from typing import Tuple, Optional
from dataclasses import dataclass
from Backend.db import get_admin_status_by_id, count_admin_couriers, count_admin_couriers_with_min_balance, get_setting
import math


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


@dataclass
class Tarifa:
    """
    Estructura que define las tarifas de envío por distancia.
    """
    base_0_2km: int
    base_2_3km: int
    extra_km_price: int


def get_tarifa_actual() -> Tarifa:
    """
    Devuelve la tarifa actual configurada.
    Por ahora valores hardcodeados, en el futuro se obtendrán de BD.

    Returns:
        Tarifa: Estructura con las tarifas actuales
    """
    return Tarifa(
        base_0_2km=5000,
        base_2_3km=6000,
        extra_km_price=1200
    )


def get_pricing_config():
    """
    Carga la configuración de precios desde BD (tabla settings).
    Retorna un dict con todos los parámetros necesarios para calcular_precio_distancia.
    """
    def to_int(val, default):
        try:
            return int(float(val))
        except:
            return default

    def to_float(val, default):
        try:
            return float(val)
        except:
            return default

    return {
        "precio_0_2km": to_int(get_setting("pricing_precio_0_2km", "5000"), 5000),
        "precio_2_3km": to_int(get_setting("pricing_precio_2_3km", "6000"), 6000),
        "base_distance_km": to_float(get_setting("pricing_base_distance_km", "3.0"), 3.0),
        "precio_km_extra_normal": to_int(get_setting("pricing_km_extra_normal", "1200"), 1200),
        "umbral_km_largo": to_float(get_setting("pricing_umbral_km_largo", "10.0"), 10.0),
        "precio_km_extra_largo": to_int(get_setting("pricing_km_extra_largo", "1000"), 1000),
    }


def calcular_precio_distancia(distancia_km: float, config: dict = None) -> int:
    """
    Calcula el precio de envío basado en la distancia con tarifa diferenciada para largas distancias.

    Reglas:
    - 0-2 km: precio_0_2km (default 5000)
    - 2.1-3 km: precio_2_3km (default 6000)
    - >3 km y <=10 km: precio_2_3km + (km_extra * precio_km_extra_normal)
    - >10 km: precio_2_3km + (km_extra * precio_km_extra_largo)

    Los km_extra se calculan con math.ceil desde base_distance_km.

    Args:
        distancia_km: Distancia en kilómetros
        config: Dict con configuración de precios. Si None, carga desde BD.

    Returns:
        Precio calculado en pesos

    Ejemplos:
        >>> calcular_precio_distancia(1.5)
        5000
        >>> calcular_precio_distancia(2.5)
        6000
        >>> calcular_precio_distancia(3.1)
        7200  # 6000 + (1 * 1200)
        >>> calcular_precio_distancia(6.1)
        10800  # 6000 + (4 * 1200)
        >>> calcular_precio_distancia(11.1)
        15000  # 6000 + (9 * 1000)
    """
    if config is None:
        config = get_pricing_config()

    precio_0_2km = config["precio_0_2km"]
    precio_2_3km = config["precio_2_3km"]
    base_distance_km = config["base_distance_km"]
    precio_km_extra_normal = config["precio_km_extra_normal"]
    umbral_km_largo = config["umbral_km_largo"]
    precio_km_extra_largo = config["precio_km_extra_largo"]

    if distancia_km <= 0:
        return 0

    if distancia_km <= 2.0:
        return precio_0_2km

    if distancia_km <= 3.0:
        return precio_2_3km

    km_extra = math.ceil(distancia_km - base_distance_km)

    precio_km_extra = precio_km_extra_largo if distancia_km > umbral_km_largo else precio_km_extra_normal

    return precio_2_3km + (km_extra * precio_km_extra)

