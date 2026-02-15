from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass
import json
import unicodedata
from db import (
    get_admin_status_by_id, count_admin_couriers, count_admin_couriers_with_min_balance, get_setting,
    count_admin_allies, count_admin_allies_with_min_balance,
    get_api_usage_today, increment_api_usage,
    get_distance_cache, upsert_distance_cache,
    get_recharge_request, insert_ledger_entry,
    get_admin_balance, update_admin_balance_with_ledger,
    update_courier_link_balance, update_ally_link_balance,
    get_courier_link_balance, get_ally_link_balance,
    get_platform_admin,
    get_approved_admin_link_for_courier, get_approved_admin_link_for_ally,
    upsert_reference_alias_candidate,
    get_connection,
)
import math
import re
import os

# Límite diario de llamadas a Google (configurable)
GOOGLE_LOOKUP_DAILY_LIMIT = int(os.getenv("GOOGLE_LOOKUP_DAILY_LIMIT", "50"))
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
DEFAULT_LOCAL_DISTANCE_FACTOR = float(os.getenv("LOCAL_DISTANCE_FACTOR", "1.3"))


def _distance_factor() -> float:
    """Factor de correccion urbana para Haversine (configurable)."""
    raw = get_setting("pricing_local_distance_factor", str(DEFAULT_LOCAL_DISTANCE_FACTOR))
    try:
        val = float(raw)
    except Exception:
        return DEFAULT_LOCAL_DISTANCE_FACTOR
    if val < 1.0:
        return 1.0
    if val > 2.0:
        return 2.0
    return val


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distancia Haversine en km entre dos coordenadas."""
    r = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlng / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def _coords_cache_key(lat: float, lng: float) -> str:
    return f"{round(lat, 5)},{round(lng, 5)}"


def _text_cache_key(text: str, city_hint: str) -> str:
    city = (city_hint or "").strip().lower()
    t = (text or "").strip().lower()
    return f"{city}|{t}"


def _normalize_reference_key(value: str) -> str:
    """Normaliza texto para matching de aliases locales."""
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower().strip()
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def _parse_local_alias_point(raw_value: Any) -> Optional[Dict[str, Any]]:
    """Convierte un alias configurado en dict canonico {lat, lng, label}."""
    if isinstance(raw_value, dict):
        try:
            lat = float(raw_value.get("lat"))
            lng = float(raw_value.get("lng"))
        except Exception:
            return None
        label = str(raw_value.get("label") or raw_value.get("address") or "").strip()
        return {"lat": lat, "lng": lng, "label": label}

    if isinstance(raw_value, (list, tuple)) and len(raw_value) >= 2:
        try:
            lat = float(raw_value[0])
            lng = float(raw_value[1])
        except Exception:
            return None
        return {"lat": lat, "lng": lng, "label": ""}

    return None


def _resolve_local_reference(text: str) -> Optional[Dict[str, Any]]:
    """
    Busca referencias locales de barrio/conjunto/punto desde settings.
    Formato esperado en `location_reference_aliases_json`:
    {
      "alfonso lopez": {"lat": 4.81, "lng": -75.69, "label": "Barrio Alfonso Lopez"},
      "terminal": [4.816, -75.69]
    }
    """
    normalized_text = _normalize_reference_key(text)
    if not normalized_text:
        return None

    raw = get_setting("location_reference_aliases_json", "")
    if not raw:
        return None

    try:
        aliases = json.loads(raw)
    except Exception:
        return None

    if not isinstance(aliases, dict):
        return None

    normalized_aliases = {}
    for alias, point in aliases.items():
        key = _normalize_reference_key(str(alias))
        parsed_point = _parse_local_alias_point(point)
        if key and parsed_point:
            normalized_aliases[key] = parsed_point

    if not normalized_aliases:
        return None

    if normalized_text in normalized_aliases:
        point = normalized_aliases[normalized_text]
        return {"lat": point["lat"], "lng": point["lng"], "method": "local_alias", "label": point["label"]}

    candidates = [k for k in normalized_aliases if k in normalized_text or normalized_text in k]
    if not candidates:
        return None
    best = max(candidates, key=len)
    point = normalized_aliases[best]
    return {"lat": point["lat"], "lng": point["lng"], "method": "local_alias", "label": point["label"]}


# ---------- HAVERSINE (DISTANCIA LOCAL GRATIS) ----------

def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Wrapper publico de _haversine_km. Retorna distancia en linea recta en km."""
    return round(_haversine_km(lat1, lng1, lat2, lng2), 2)


def haversine_road_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Distancia estimada por carretera urbana = Haversine * factor de correccion configurable.
    Factor por defecto 1.30 (calles urbanas tipicas agregan ~30% sobre linea recta).
    Configurable via BD (pricing_local_distance_factor) o env (LOCAL_DISTANCE_FACTOR).
    """
    straight = _haversine_km(lat1, lng1, lat2, lng2)
    return round(straight * _distance_factor(), 2)


# ---------- GOOGLE API HELPERS ----------

def can_call_google_today() -> bool:
    """Verifica si podemos hacer más llamadas a Google hoy (fusible)."""
    usage = get_api_usage_today("google_maps")
    return usage < GOOGLE_LOOKUP_DAILY_LIMIT


def extract_place_id_from_url(url: str) -> Optional[str]:
    """Extrae place_id de una URL de Google Maps si existe."""
    if not url:
        return None
    # Patrones comunes: place_id=xxx, query_place_id=xxx, /place/xxx/
    patterns = [
        r'place_id=([A-Za-z0-9_-]+)',
        r'query_place_id=([A-Za-z0-9_-]+)',
        r'/place/[^/]+/data=[^/]*!1s([A-Za-z0-9_-]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def google_place_details(place_id: str) -> Optional[Dict[str, Any]]:
    """Obtiene detalles de un lugar por place_id usando Places API."""
    if not GOOGLE_MAPS_API_KEY or not place_id:
        return None
    try:
        import requests
        url = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            "place_id": place_id,
            "fields": "geometry,formatted_address,name",
            "key": GOOGLE_MAPS_API_KEY
        }
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        if data.get("status") == "OK" and data.get("result"):
            result = data["result"]
            geo = result.get("geometry", {}).get("location", {})
            increment_api_usage("google_maps")
            return {
                "lat": geo.get("lat"),
                "lng": geo.get("lng"),
                "formatted_address": result.get("formatted_address"),
                "place_id": place_id,
                "provider": "google_places"
            }
    except Exception:
        pass
    return None


def google_geocode_forward(query: str) -> Optional[Dict[str, Any]]:
    """Geocodifica una dirección de texto usando Geocoding API."""
    if not GOOGLE_MAPS_API_KEY or not query:
        return None
    try:
        import requests
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "address": query,
            "key": GOOGLE_MAPS_API_KEY
        }
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        if data.get("status") == "OK" and data.get("results"):
            result = data["results"][0]
            geo = result.get("geometry", {}).get("location", {})
            increment_api_usage("google_maps")
            return {
                "lat": geo.get("lat"),
                "lng": geo.get("lng"),
                "formatted_address": result.get("formatted_address"),
                "place_id": result.get("place_id"),
                "provider": "google_geocode"
            }
    except Exception:
        pass
    return None


# ---------- PARSER DE LINKS / COORDS ----------

def expand_short_url(text: str) -> Optional[str]:
    """Expande links cortos de Google Maps (maps.app.goo.gl / goo.gl)."""
    if not text:
        return None
    text = text.strip()
    if "http" in text and ("maps.app.goo.gl" in text or "goo.gl" in text):
        try:
            import requests
            url = next((t for t in text.split() if t.startswith("http")), None)
            if url:
                headers = {"User-Agent": "Mozilla/5.0 (compatible; DomiBot/1.0)"}
                r = requests.get(url, allow_redirects=True, timeout=10, headers=headers)
                return r.url or url
        except Exception:
            return None
    return None


def extract_lat_lng_from_text(text: str) -> Optional[Tuple[float, float]]:
    """
    Extrae lat/lng de texto/URL expandida.
    NOTA: Si el texto es un link corto (goo.gl), debe expandirse ANTES con expand_short_url().

    Retorna (lat, lng) o None si no se puede extraer.
    Valida rangos: lat [-90, 90], lng [-180, 180]
    """
    if not text:
        return None

    text = text.strip()

    # Patrones para extraer coords de URLs de Google Maps
    patterns = [
        r'[?&]q=(-?\d+\.?\d*),(-?\d+\.?\d*)',           # ?q=4.81,-75.69
        r'@(-?\d+\.?\d*),(-?\d+\.?\d*)',                 # @4.81,-75.69,17z
        r'/place/[^/]+/@(-?\d+\.?\d*),(-?\d+\.?\d*)',   # /place/.../@4.81,-75.69
        r'!3d(-?\d+\.?\d*)!4d(-?\d+\.?\d*)',            # !3d4.81!4d-75.69
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                lat = float(match.group(1))
                lng = float(match.group(2))
                if -90 <= lat <= 90 and -180 <= lng <= 180:
                    return (lat, lng)
            except (ValueError, IndexError):
                continue

    # Patron 2: Coordenadas directas "lat,lng" o "lat, lng"
    direct_pattern = r'^(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)$'
    match = re.match(direct_pattern, text)
    if match:
        try:
            lat = float(match.group(1))
            lng = float(match.group(2))
            if -90 <= lat <= 90 and -180 <= lng <= 180:
                return (lat, lng)
        except ValueError:
            pass

    return None


# ---------- DISTANCE MATRIX POR COORDENADAS ----------

def get_distance_from_api_coords(lat1: float, lng1: float, lat2: float, lng2: float) -> Optional[float]:
    """
    Calcula distancia en km entre dos puntos usando Google Distance Matrix API con coordenadas.

    Args:
        lat1, lng1: Coordenadas de origen
        lat2, lng2: Coordenadas de destino

    Returns:
        Distancia en km o None si falla
    """
    import os
    import requests

    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return None

    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": f"{lat1},{lng1}",
        "destinations": f"{lat2},{lng2}",
        "key": api_key,
        "units": "metric",
        "language": "es",
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if data.get("status") != "OK":
            return None

        rows = data.get("rows", [])
        if not rows:
            return None

        elements = rows[0].get("elements", [])
        if not elements:
            return None

        element = elements[0]
        if element.get("status") != "OK":
            return None

        distance_meters = element.get("distance", {}).get("value", 0)
        distance_km = distance_meters / 1000.0
        increment_api_usage("google_maps")
        return round(distance_km, 2)

    except Exception:
        return None


def get_smart_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> dict:
    """
    Estrategia en 3 capas para calcular distancia de forma economica:

    Capa 1 - Haversine: calculo local gratuito (distancia * factor urbano).
    Capa 2 - Cache: busca si ya calculamos esta ruta antes (map_distance_cache).
    Capa 3 - Google API: solo si hay cuota disponible (costoso).

    Retorna dict con: distance_km, source ('cache'|'haversine'|'google'), used_api (bool)
    """
    origin_key = _coords_cache_key(lat1, lng1)
    destination_key = _coords_cache_key(lat2, lng2)

    # --- CAPA 1: Haversine (primera opcion, gratis) ---
    haversine_dist = round(_haversine_km(lat1, lng1, lat2, lng2) * _distance_factor(), 2)
    local_result = {
        "distance_km": haversine_dist,
        "source": "haversine",
        "used_api": False,
    }

    # --- CAPA 2: Cache ---
    cached = get_distance_cache(origin_key, destination_key, mode="coords")
    if cached and cached.get("distance_km") is not None:
        return {
            "distance_km": float(cached["distance_km"]),
            "source": f"cache({cached.get('provider', 'unknown')})",
            "used_api": False,
        }

    # Si no hay cache, guardamos resultado local para siguientes consultas.
    upsert_distance_cache(origin_key, destination_key, mode="coords",
                          distance_km=haversine_dist, provider="haversine")

    # --- CAPA 3: Google API (solo si hay cuota) ---
    # En cotizacion por coords casi nunca es necesario, pero se mantiene como ultimo recurso
    # cuando no hay un valor local util.
    if haversine_dist <= 0 and can_call_google_today() and GOOGLE_MAPS_API_KEY:
        google_dist = get_distance_from_api_coords(lat1, lng1, lat2, lng2)
        if google_dist is not None:
            upsert_distance_cache(origin_key, destination_key, mode="coords",
                                  distance_km=google_dist, provider="google_distance_matrix")
            return {
                "distance_km": google_dist,
                "source": "google",
                "used_api": True,
            }

    # Fusible/fallback: continuar con estimacion local.
    return local_result


def quote_order_by_coords(pickup_lat: float, pickup_lng: float, dropoff_lat: float, dropoff_lng: float) -> dict:
    """
    Calcula cotizacion usando coordenadas con estrategia economica en 3 capas:
    1. Cache de distancias previas
    2. Haversine local (gratis)
    3. Google API (solo si hay cuota)

    Args:
        pickup_lat, pickup_lng: Coordenadas de recogida
        dropoff_lat, dropoff_lng: Coordenadas de entrega

    Returns:
        dict con: success, distance_km, price, quote_source, config, distance_source
    """
    result = get_smart_distance(pickup_lat, pickup_lng, dropoff_lat, dropoff_lng)
    distance_km = result["distance_km"]

    config = get_pricing_config()
    price = calcular_precio_distancia(distance_km, config)

    return {
        "success": True,
        "distance_km": distance_km,
        "price": price,
        "config": config,
        "quote_source": "coords",
        "distance_source": result["source"],
        "used_api": result["used_api"],
    }


def admin_puede_operar(admin_id: int, min_couriers: int = 5, min_allies: int = 5,
                        min_balance: int = 5000, min_admin_balance: int = 60000):
    """
    Regla de negocio: un admin local puede operar si:
    1. Está APPROVED
    2. Tiene al menos min_allies aliados con balance >= min_balance
    3. Tiene al menos min_couriers repartidores con balance >= min_balance
    4. Su saldo master es >= min_admin_balance

    Retorna:
    (puede_operar, motivo, stats_dict)
    stats_dict tiene: total_couriers, couriers_ok, total_allies, allies_ok, admin_balance
    """
    status = get_admin_status_by_id(admin_id)
    if not status:
        return False, "Administrador no encontrado.", {}

    if status != "APPROVED":
        return False, "Estado actual: {}.".format(status), {}

    total_couriers = count_admin_couriers(admin_id)
    couriers_ok = count_admin_couriers_with_min_balance(admin_id, min_balance=min_balance)
    total_allies = count_admin_allies(admin_id)
    allies_ok = count_admin_allies_with_min_balance(admin_id, min_balance=min_balance)
    admin_balance = get_admin_balance(admin_id)

    stats = {
        "total_couriers": total_couriers,
        "couriers_ok": couriers_ok,
        "total_allies": total_allies,
        "allies_ok": allies_ok,
        "admin_balance": admin_balance,
    }

    problemas = []
    if allies_ok < min_allies:
        problemas.append("Aliados con saldo >= ${:,}: {}/{}.".format(min_balance, allies_ok, min_allies))
    if couriers_ok < min_couriers:
        problemas.append("Repartidores con saldo >= ${:,}: {}/{}.".format(min_balance, couriers_ok, min_couriers))
    if admin_balance < min_admin_balance:
        problemas.append("Saldo master: ${:,} / ${:,} requerido.".format(admin_balance, min_admin_balance))

    if problemas:
        return False, " | ".join(problemas), stats

    return True, "OK", stats


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


def _to_int(val, default):
    try:
        return int(float(val))
    except:
        return default


def _to_float(val, default):
    try:
        return float(val)
    except:
        return default


def get_pricing_config():
    """
    Carga la configuración de precios desde BD (tabla settings).
    Retorna un dict con todos los parámetros necesarios para calcular_precio_distancia.
    """
    return {
        "precio_0_2km": _to_int(get_setting("pricing_precio_0_2km", "5000"), 5000),
        "precio_2_3km": _to_int(get_setting("pricing_precio_2_3km", "6000"), 6000),
        "base_distance_km": _to_float(get_setting("pricing_base_distance_km", "3.0"), 3.0),
        "precio_km_extra_normal": _to_int(get_setting("pricing_km_extra_normal", "1200"), 1200),
        "umbral_km_largo": _to_float(get_setting("pricing_umbral_km_largo", "10.0"), 10.0),
        "precio_km_extra_largo": _to_int(get_setting("pricing_km_extra_largo", "1000"), 1000),
    }


def get_buy_pricing_config():
    """Carga la configuracion de recargos por productos (Compras) desde BD."""
    return {
        "tier1_max": _to_int(get_setting("buy_tier1_max", "5"), 5),
        "tier1_fee": _to_int(get_setting("buy_tier1_fee", "1000"), 1000),
        "tier2_max": _to_int(get_setting("buy_tier2_max", "5"), 5),
        "tier2_fee": _to_int(get_setting("buy_tier2_fee", "700"), 700),
        "tier3_fee": _to_int(get_setting("buy_tier3_fee", "500"), 500),
    }


def calc_buy_products_surcharge(n_products: int, config: dict = None) -> int:
    """
    Calcula el recargo por productos para servicio de Compras.

    Tramos:
    - 1 a tier1_max (default 5): +tier1_fee c/u
    - tier1_max+1 a tier1_max+tier2_max (default 6-10): +tier2_fee c/u
    - tier1_max+tier2_max+1 en adelante (default 11+): +tier3_fee c/u

    Args:
        n_products: Numero de productos
        config: Dict con configuracion. Si None, carga desde BD.

    Returns:
        Recargo total en pesos
    """
    if n_products <= 0:
        return 0

    if config is None:
        config = get_buy_pricing_config()

    tier1_max = config["tier1_max"]
    tier1_fee = config["tier1_fee"]
    tier2_max = config["tier2_max"]
    tier2_fee = config["tier2_fee"]
    tier3_fee = config["tier3_fee"]

    tier1 = min(n_products, tier1_max) * tier1_fee
    tier2 = min(max(n_products - tier1_max, 0), tier2_max) * tier2_fee
    tier3 = max(n_products - tier1_max - tier2_max, 0) * tier3_fee

    return tier1 + tier2 + tier3


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


def quote_order(distance_km: float) -> dict:
    """
    Calcula cotizacion de un pedido basado en la distancia.
    Reutiliza la misma formula de /cotizar.

    Args:
        distance_km: Distancia en kilometros

    Returns:
        dict con: distance_km, price, config (tarifas usadas)
    """
    config = get_pricing_config()
    price = calcular_precio_distancia(distance_km, config)

    return {
        "distance_km": distance_km,
        "price": price,
        "config": config
    }


def get_distance_from_api(origin: str, destination: str, city_hint: str = "Pereira, Colombia") -> Optional[float]:
    """
    Calcula la distancia en km entre dos direcciones usando Google Distance Matrix API.

    Args:
        origin: Direccion de origen (pickup)
        destination: Direccion de destino (dropoff)
        city_hint: Ciudad para mejorar precision (default: Pereira, Colombia)

    Returns:
        Distancia en km o None si falla la API o no hay API key
    """
    import os
    import requests

    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return None

    # Agregar ciudad si no esta presente
    if city_hint and city_hint.lower() not in origin.lower():
        origin = f"{origin}, {city_hint}"
    if city_hint and city_hint.lower() not in destination.lower():
        destination = f"{destination}, {city_hint}"

    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": origin,
        "destinations": destination,
        "key": api_key,
        "units": "metric",
        "language": "es",
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if data.get("status") != "OK":
            return None

        rows = data.get("rows", [])
        if not rows:
            return None

        elements = rows[0].get("elements", [])
        if not elements:
            return None

        element = elements[0]
        if element.get("status") != "OK":
            return None

        distance_meters = element.get("distance", {}).get("value", 0)
        distance_km = distance_meters / 1000.0
        increment_api_usage("google_maps")
        return round(distance_km, 2)

    except Exception:
        return None


def quote_order_by_addresses(pickup_text: str, dropoff_text: str, city_hint: str = "Pereira, Colombia") -> dict:
    """
    Calcula cotizacion de un pedido usando direcciones (fallback cuando no hay coords).

    Args:
        pickup_text: Direccion de recogida
        dropoff_text: Direccion de entrega
        city_hint: Ciudad para mejorar precision de la API

    Returns:
        dict con: distance_km, price, config, success, quote_source
        Si la API falla, distance_km y price seran None
    """
    config = get_pricing_config()

    # 1) Capa local gratis si el texto trae coordenadas
    pickup_coords = extract_lat_lng_from_text(pickup_text)
    dropoff_coords = extract_lat_lng_from_text(dropoff_text)
    if pickup_coords and dropoff_coords:
        coords_quote = quote_order_by_coords(
            pickup_coords[0], pickup_coords[1],
            dropoff_coords[0], dropoff_coords[1]
        )
        if coords_quote.get("success"):
            return {
                "distance_km": coords_quote["distance_km"],
                "price": coords_quote["price"],
                "config": coords_quote["config"],
                "success": True,
                "quote_source": "text_via_" + str(coords_quote.get("quote_source")),
            }

    # 2) Cache por par de direcciones
    origin_key = _text_cache_key(pickup_text, city_hint)
    destination_key = _text_cache_key(dropoff_text, city_hint)
    cached = get_distance_cache(origin_key, destination_key, mode="text")
    if cached and cached.get("distance_km") is not None:
        distance_km = float(cached["distance_km"])
        price = calcular_precio_distancia(distance_km, config)
        return {
            "distance_km": distance_km,
            "price": price,
            "config": config,
            "success": True,
            "quote_source": "text_cache",
        }

    # 3) API paga como ultimo recurso (si hay cuota diaria)
    if can_call_google_today():
        distance_km = get_distance_from_api(pickup_text, dropoff_text, city_hint)
        if distance_km is not None:
            upsert_distance_cache(origin_key, destination_key, mode="text", distance_km=distance_km, provider="google_distance_matrix")
            price = calcular_precio_distancia(distance_km, config)
            return {
                "distance_km": distance_km,
                "price": price,
                "config": config,
                "success": True,
                "quote_source": "text_api",
            }

    # 4) Fusible/fallback local para no romper flujo sin cuota/API
    fallback_distance = float(config["base_distance_km"])
    price = calcular_precio_distancia(fallback_distance, config)
    return {
        "distance_km": fallback_distance,
        "price": price,
        "config": config,
        "success": True,
        "quote_source": "text_fallback_local",
    }


# ---------- RESOLVER UBICACION INTELIGENTE ----------

def resolve_location(text: str) -> Optional[Dict[str, Any]]:
    """
    Intenta extraer lat/lng de cualquier entrada del usuario:
    1. Coordenadas directas (4.81,-75.69)
    2. Link de Google Maps (corto o largo)
    3. Geocoding con Google API (solo si hay cuota)

    Retorna dict {lat, lng, method} o None.
    """
    if not text:
        return None

    text = text.strip()
    is_url_like = "http" in text.lower()

    # 1. Intentar extraer coords directamente
    coords = extract_lat_lng_from_text(text)
    if coords:
        return {"lat": coords[0], "lng": coords[1], "method": "coords"}

    # 2. Si es link corto, expandir primero
    expanded = expand_short_url(text)
    if expanded:
        coords = extract_lat_lng_from_text(expanded)
        if coords:
            return {"lat": coords[0], "lng": coords[1], "method": "link"}

        # Intentar extraer place_id del link expandido
        place_id = extract_place_id_from_url(expanded)
        if place_id and can_call_google_today():
            details = google_place_details(place_id)
            if details and details.get("lat") and details.get("lng"):
                return {"lat": details["lat"], "lng": details["lng"], "method": "places_api"}

    # 3. Si es link largo de Google Maps
    if "google" in text.lower() or "maps" in text.lower() or "goo.gl" in text.lower():
        place_id = extract_place_id_from_url(text)
        if place_id and can_call_google_today():
            details = google_place_details(place_id)
            if details and details.get("lat") and details.get("lng"):
                return {"lat": details["lat"], "lng": details["lng"], "method": "places_api"}

    # 4. Referencias locales (gratis): barrio/conjunto/punto configurado.
    local_ref = _resolve_local_reference(text)
    if local_ref:
        return local_ref

    # 5. Geocoding por texto (ultimo recurso, cuesta API)
    normalized_text = _normalize_reference_key(text)
    if can_call_google_today() and not is_url_like:
        geo = google_geocode_forward(text)
        if geo and geo.get("lat") and geo.get("lng"):
            upsert_reference_alias_candidate(
                raw_text=text,
                normalized_text=normalized_text,
                suggested_lat=geo["lat"],
                suggested_lng=geo["lng"],
                source="geocode",
            )
            return {"lat": geo["lat"], "lng": geo["lng"], "method": "geocode"}

    if not is_url_like:
        upsert_reference_alias_candidate(
            raw_text=text,
            normalized_text=normalized_text,
            source="unresolved",
        )
    return None


# ============================================================
# SISTEMA DE RECARGAS
# ============================================================

def approve_recharge_request(request_id: int, decided_by_admin_id: int) -> Tuple[bool, str]:
    """
    Aprueba una solicitud de recarga.
    - Si el admin asignado es LOCAL: valida saldo y descuenta del admin.
    - Si el admin asignado es PLATAFORMA: acredita sin validar saldo.
    Registra el movimiento en ledger.

    Retorna: (success, message)
    """
    req = get_recharge_request(request_id)
    if not req:
        return False, "Solicitud no encontrada."

    target_type = req["target_type"]
    target_id = req["target_id"]
    admin_id = req["admin_id"]
    amount = req["amount"]
    status = req["status"]

    if status != "PENDING":
        return False, f"Solicitud ya procesada (status: {status})."

    platform_admin = get_platform_admin()
    is_platform = bool(platform_admin and platform_admin["id"] == admin_id)

    if target_type == "ADMIN":
        # Admin local recargando con plataforma: no necesita vínculo,
        # se acredita directamente el saldo master del admin
        pass
    elif target_type == "COURIER":
        link = get_approved_admin_link_for_courier(target_id)
        if not link or link["admin_id"] != admin_id:
            return False, "No hay vinculo APPROVED con este admin para acreditar saldo."
    elif target_type == "ALLY":
        link = get_approved_admin_link_for_ally(target_id)
        if not link or link["admin_id"] != admin_id:
            return False, "No hay vinculo APPROVED con este admin para acreditar saldo."
    else:
        return False, f"Tipo de destino desconocido: {target_type}"

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE")

        if not is_platform:
            cur.execute("SELECT balance FROM admins WHERE id = ?", (admin_id,))
            row = cur.fetchone()
            current_admin_balance = row["balance"] if row else 0
            if current_admin_balance < amount:
                conn.rollback()
                return False, f"Saldo insuficiente. Tienes ${current_admin_balance:,} y se requieren ${amount:,}."

            cur.execute(
                "UPDATE admins SET balance = balance - ? WHERE id = ?",
                (amount, admin_id),
            )
            cur.execute("""
                INSERT INTO ledger
                    (kind, from_type, from_id, to_type, to_id, amount, ref_type, ref_id, note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "RECHARGE", "ADMIN", admin_id, "ADMIN", admin_id, amount,
                "RECHARGE_REQUEST", request_id,
                f"Recarga aprobada por admin_id={decided_by_admin_id} a {target_type} id={target_id}",
            ))

        if target_type == "ADMIN":
            cur.execute(
                "UPDATE admins SET balance = balance + ? WHERE id = ?",
                (amount, target_id),
            )
            cur.execute("""
                INSERT INTO ledger
                    (kind, from_type, from_id, to_type, to_id, amount, ref_type, ref_id, note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "RECHARGE", "PLATFORM", admin_id, "ADMIN", target_id, amount,
                "RECHARGE_REQUEST", request_id,
                f"Recarga de admin local aprobada por plataforma admin_id={decided_by_admin_id}",
            ))
        elif target_type == "COURIER":
            cur.execute("""
                UPDATE admin_couriers
                SET balance = balance + ?, updated_at = datetime('now')
                WHERE courier_id = ? AND admin_id = ? AND status = 'APPROVED'
            """, (amount, target_id, admin_id))
            if cur.rowcount != 1:
                conn.rollback()
                return False, "No hay vinculo APPROVED con este admin para acreditar saldo."
            cur.execute("""
                INSERT INTO ledger
                    (kind, from_type, from_id, to_type, to_id, amount, ref_type, ref_id, note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "RECHARGE", "PLATFORM" if is_platform else "ADMIN", admin_id, "COURIER", target_id, amount,
                "RECHARGE_REQUEST", request_id,
                f"Recarga aprobada por admin_id={decided_by_admin_id}",
            ))
        elif target_type == "ALLY":
            cur.execute("""
                UPDATE admin_allies
                SET balance = balance + ?, updated_at = datetime('now')
                WHERE ally_id = ? AND admin_id = ? AND status = 'APPROVED'
            """, (amount, target_id, admin_id))
            if cur.rowcount != 1:
                conn.rollback()
                return False, "No hay vinculo APPROVED con este admin para acreditar saldo."
            cur.execute("""
                INSERT INTO ledger
                    (kind, from_type, from_id, to_type, to_id, amount, ref_type, ref_id, note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "RECHARGE", "PLATFORM" if is_platform else "ADMIN", admin_id, "ALLY", target_id, amount,
                "RECHARGE_REQUEST", request_id,
                f"Recarga aprobada por admin_id={decided_by_admin_id}",
            ))
        else:
            conn.rollback()
            return False, f"Tipo de destino desconocido: {target_type}"

        cur.execute("""
            UPDATE recharge_requests
            SET status = 'APPROVED', decided_by_admin_id = ?, decided_at = datetime('now')
            WHERE id = ? AND status = 'PENDING'
        """, (decided_by_admin_id, request_id))
        if cur.rowcount != 1:
            conn.rollback()
            return False, "Solicitud ya procesada."

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return True, "Recarga aprobada exitosamente."


def reject_recharge_request(request_id: int, decided_by_admin_id: int, note: str = None) -> Tuple[bool, str]:
    """
    Rechaza una solicitud de recarga.
    No modifica saldos, solo actualiza el status.

    Retorna: (success, message)
    """
    req = get_recharge_request(request_id)
    if not req:
        return False, "Solicitud no encontrada."

    status = req["status"]
    if status != "PENDING":
        return False, f"Solicitud ya procesada (status: {status})."

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE recharge_requests
            SET status = 'REJECTED', decided_by_admin_id = ?, decided_at = datetime('now')
            WHERE id = ? AND status = 'PENDING'
        """, (decided_by_admin_id, request_id))
        if cur.rowcount != 1:
            conn.rollback()
            return False, "Solicitud ya procesada."
        conn.commit()
    finally:
        conn.close()

    return True, "Solicitud de recarga rechazada."


def apply_service_fee(target_type: str, target_id: int, admin_id: int,
                      ref_type: str = None, ref_id: int = None) -> Tuple[bool, str]:
    """
    Cobra tarifa de $300 por servicio al courier/aliado.
    - Si admin es PLATFORM: 300 van a plataforma.
    - Si admin es local: 300 del miembro + 100 del admin (comision plataforma).
    Retorna: (success, message)
    """
    fee = 300
    platform_commission = 100

    platform_admin = get_platform_admin()
    is_platform = platform_admin and platform_admin["id"] == admin_id

    if target_type == "COURIER":
        balance = get_courier_link_balance(target_id, admin_id)
    elif target_type == "ALLY":
        balance = get_ally_link_balance(target_id, admin_id)
    else:
        return False, "Tipo de destino desconocido: {}".format(target_type)

    if balance < fee:
        return False, "Saldo insuficiente. Balance: ${:,}, requerido: ${:,}.".format(balance, fee)

    if not is_platform:
        admin_balance = get_admin_balance(admin_id)
        if admin_balance < platform_commission:
            return False, "ADMIN_SIN_SALDO"

    if target_type == "COURIER":
        update_courier_link_balance(target_id, admin_id, -fee)
    elif target_type == "ALLY":
        update_ally_link_balance(target_id, admin_id, -fee)

    insert_ledger_entry(
        kind="FEE",
        from_type=target_type,
        from_id=target_id,
        to_type="ADMIN",
        to_id=admin_id,
        amount=fee,
        ref_type=ref_type,
        ref_id=ref_id,
        note="Tarifa de servicio"
    )

    if not is_platform:
        update_admin_balance_with_ledger(
            admin_id=admin_id,
            delta=-platform_commission,
            kind="PLATFORM_FEE",
            note="Comision plataforma por servicio de {} id={}".format(target_type, target_id),
            ref_type=ref_type,
            ref_id=ref_id,
            from_type="ADMIN",
            from_id=admin_id,
        )

    return True, "Tarifa de ${:,} aplicada.".format(fee)


def check_service_fee_available(target_type: str, target_id: int, admin_id: int) -> Tuple[bool, str]:
    """
    Verifica si hay saldo suficiente para cobrar el fee, sin cobrar.
    Retorna: (can_operate, error_code)
    error_code: 'OK', 'MEMBER_SIN_SALDO', 'ADMIN_SIN_SALDO'
    """
    fee = 300
    platform_commission = 100

    platform_admin = get_platform_admin()
    is_platform = platform_admin and platform_admin["id"] == admin_id

    if target_type == "COURIER":
        balance = get_courier_link_balance(target_id, admin_id)
    elif target_type == "ALLY":
        balance = get_ally_link_balance(target_id, admin_id)
    else:
        return False, "UNKNOWN_TYPE"

    if balance < fee:
        return False, "MEMBER_SIN_SALDO"

    if not is_platform:
        admin_balance = get_admin_balance(admin_id)
        if admin_balance < platform_commission:
            return False, "ADMIN_SIN_SALDO"

    return True, "OK"


# TODO: Fase 2 - Implementar cobro al courier cuando complete entrega
# Usar apply_service_fee(target_type="COURIER", target_id=courier_id, admin_id=admin_id, ref_type="ORDER", ref_id=order_id)

