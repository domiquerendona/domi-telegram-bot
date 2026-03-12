from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass
import json
import logging
import unicodedata

logger = logging.getLogger(__name__)
from db import (
    get_admin_status_by_id, count_admin_couriers, count_admin_couriers_with_min_balance, get_setting,
    set_setting,
    count_admin_allies, count_admin_allies_with_min_balance,
    get_api_usage_today, record_api_usage_event,
    get_api_usage_cost_summary,
    get_distance_cache, upsert_distance_cache,
    get_recharge_request, insert_ledger_entry,
    get_admin_balance, update_admin_balance_with_ledger,
    register_platform_income,
    update_courier_link_balance, update_ally_link_balance,
    credit_welcome_balance,
    get_courier_link_balance, get_ally_link_balance,
    get_platform_admin,
    get_approved_admin_link_for_courier, get_approved_admin_link_for_ally,
    get_approved_admin_id_for_courier,
    upsert_reference_alias_candidate,
    list_reference_alias_candidates,
    get_reference_alias_candidate_by_id,
    review_reference_alias_candidate,
    set_reference_alias_candidate_coords,
    get_connection,
    P,
    DB_ENGINE,
    get_order_status_by_id,
    cancel_order,
    get_admin_by_telegram_id,
    get_user_by_telegram_id,
    get_admin_by_user_id,
    can_admin_validate_references,
    get_courier_telegram_id,
    get_ally_telegram_id,
    create_profile_change_request,
    has_pending_profile_change_request,
    list_pending_profile_change_requests,
    get_profile_change_request_by_id,
    mark_profile_change_request_approved,
    mark_profile_change_request_rejected,
    apply_profile_change_request_data,
    sync_all_courier_link_statuses,
    # Re-exports para que main.py no acceda a db directamente
    ensure_user,
    get_user_by_id,
    get_available_admin_teams,
    get_admin_rejection_type_by_id,
    get_ally_rejection_type_by_id,
    get_courier_rejection_type_by_id,
    list_approved_admin_teams,
    list_courier_links_by_admin,
    list_ally_links_by_admin,
    get_platform_admin_id,
    upsert_admin_ally_link,
    create_admin_courier_link,
    deactivate_other_approved_admin_courier_links,
    deactivate_other_approved_admin_ally_links,
    get_local_admins_count,
    create_ally,
    get_ally_by_user_id,
    get_pending_allies,
    get_ally_by_id,
    update_ally_status,
    update_ally_status_by_id,
    get_all_allies,
    update_ally,
    delete_ally,
    create_admin,
    user_has_platform_admin,
    get_all_admins,
    get_pending_admins,
    get_admin_by_id,
    update_admin_status_by_id,
    get_admin_by_team_code,
    update_admin_courier_status,
    upsert_admin_courier_link,
    create_ally_location,
    get_ally_locations,
    get_ally_location_by_id,
    get_default_ally_location,
    set_default_ally_location,
    update_ally_location,
    update_ally_location_coords,
    delete_ally_location,
    increment_pickup_usage,
    set_frequent_pickup,
    create_courier,
    get_courier_by_user_id,
    get_courier_by_id,
    get_courier_by_telegram_id,
    set_courier_available_cash,
    deactivate_courier,
    update_courier_live_location,
    set_courier_availability,
    expire_stale_live_locations,
    get_pending_couriers,
    get_pending_couriers_by_admin,
    get_pending_allies_by_admin,
    get_allies_by_admin_and_status,
    get_couriers_by_admin_and_status,
    update_courier_status,
    update_courier_status_by_id,
    get_all_couriers,
    update_courier,
    delete_courier,
    get_admin_link_for_courier,
    get_admin_link_for_ally,
    get_courier_link_balance,
    get_approved_admin_id_for_courier,
    create_order,
    set_order_status,
    assign_order_to_courier,
    get_order_by_id,
    add_order_incentive,
    get_orders_by_ally,
    get_orders_by_courier,
    get_courier_daily_earnings_history,
    get_courier_earnings_by_date,
    get_totales_registros,
    add_courier_rating,
    get_active_terms_version,
    has_accepted_terms,
    save_terms_acceptance,
    save_terms_session_ack,
    create_ally_customer,
    update_ally_customer,
    archive_ally_customer,
    restore_ally_customer,
    get_ally_customer_by_id,
    get_ally_customer_by_phone,
    list_ally_customers,
    search_ally_customers,
    create_customer_address,
    update_customer_address,
    archive_customer_address,
    restore_customer_address,
    get_customer_address_by_id,
    list_customer_addresses,
    get_last_order_by_ally,
    get_recent_delivery_addresses_for_ally,
    get_link_cache,
    upsert_link_cache,
    get_all_approved_links_for_courier,
    get_all_approved_links_for_ally,
    ensure_platform_temp_coverage_for_ally,
    create_recharge_request,
    list_pending_recharges_for_admin,
    list_all_pending_recharges,
    get_admins_with_pending_count,
    list_recharge_ledger,
    get_admin_payment_info,
    update_admin_payment_info,
    update_recharge_proof,
    create_payment_method,
    get_payment_method_by_id,
    list_payment_methods,
    toggle_payment_method,
    deactivate_payment_method,
    get_admin_reference_validator_permission,
    set_admin_reference_validator_permission,
    # Re-exports rutas multi-parada
    create_route,
    create_route_destination,
    get_route_by_id,
    get_route_destinations,
    get_pending_route_stops,
    update_route_status,
    assign_route_to_courier,
    deliver_route_stop,
    cancel_route,
    create_route_offer_queue,
    get_next_pending_route_offer,
    mark_route_offer_as_offered,
    mark_route_offer_response,
    get_current_route_offer,
    delete_route_offer_queue,
    reset_route_offer_queue,
    get_all_online_couriers,
    get_active_orders_without_courier,
    block_courier_for_ally,
    unblock_courier_for_ally,
    get_blocked_courier_ids_for_ally,
    set_courier_arrived,
    set_courier_accepted_location,
    get_active_order_for_courier,
    get_active_route_for_courier,
    get_courier_delivery_time_stats,
    get_all_local_admins,
    # Re-exports admin_locations
    create_admin_location,
    get_admin_locations,
    get_admin_location_by_id,
    get_default_admin_location,
    set_default_admin_location,
    increment_admin_location_usage,
    archive_admin_location,
    update_admin_location,
    create_admin_customer,
    update_admin_customer,
    archive_admin_customer,
    restore_admin_customer,
    get_admin_customer_by_id,
    get_admin_customer_by_phone,
    list_admin_customers,
    search_admin_customers,
    create_admin_customer_address,
    update_admin_customer_address,
    archive_admin_customer_address,
    restore_admin_customer_address,
    get_admin_customer_address_by_id,
    list_admin_customer_addresses,
    # Re-exports offer queue
    clear_offer_queue,
    # Re-exports order_support_requests
    create_order_support_request,
    get_pending_support_request,
    resolve_support_request,
    cancel_route_stop,
    get_all_pending_support_requests,
    get_support_request_full,
    get_all_orders,
    get_admin_panel_balances_data,
    get_admin_panel_users_data,
    get_admin_panel_earnings_data,
    get_dashboard_stats_data,
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


def get_online_couriers_sorted_by_distance(lat: float, lng: float) -> list:
    """
    Retorna todos los repartidores ONLINE ordenados por distancia (km) al punto dado.
    Usa live_lat/live_lng si disponible; fallback a residence_lat/residence_lng.
    Agrega campo 'distancia_km' a cada registro.
    """
    couriers = get_all_online_couriers()
    result = []
    for c in couriers:
        c_lat = c["live_lat"] or c["residence_lat"]
        c_lng = c["live_lng"] or c["residence_lng"]
        if c_lat and c_lng:
            dist = _haversine_km(lat, lng, float(c_lat), float(c_lng))
        else:
            dist = 9999.0
        row = dict(c)
        row["distancia_km"] = round(dist, 2)
        result.append(row)
    result.sort(key=lambda x: x["distancia_km"])
    return result


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
    result = usage < GOOGLE_LOOKUP_DAILY_LIMIT
    logger.warning("[QUOTA] usage=%s limit=%s can_call=%s", usage, GOOGLE_LOOKUP_DAILY_LIMIT, result)
    return result


def _google_cost_usd(api_operation: str) -> float:
    """
    Lee costo estimado por operación desde env.

    Env var: GOOGLE_COST_USD_{API_OPERATION}
    Ej: GOOGLE_COST_USD_PLACE_DETAILS, GOOGLE_COST_USD_DISTANCE_MATRIX_TEXT
    """
    import os
    if not api_operation:
        return 0.0
    key = f"GOOGLE_COST_USD_{api_operation.upper()}"
    raw = os.environ.get(key, "") or ""
    try:
        return float(raw) if raw.strip() else 0.0
    except Exception:
        return 0.0


def get_google_maps_cost_summary(days: int = 7):
    """
    Resumen de costo estimado de Google Maps por operación en los últimos N días.
    """
    try:
        from datetime import date, timedelta
        d = int(days or 0)
        if d <= 0:
            d = 7
        to_date = date.today().isoformat()
        from_date = (date.today() - timedelta(days=d - 1)).isoformat()
        return get_api_usage_cost_summary("google_maps", from_date, to_date)
    except Exception:
        return []


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
        status = data.get("status")
        ok = status == "OK" and bool(data.get("result"))
        record_api_usage_event(
            "google_maps",
            "place_details",
            success=ok,
            units=1,
            units_kind="call",
            cost_usd=_google_cost_usd("place_details"),
            http_status=getattr(r, "status_code", None),
            provider_status=status,
            error_message=data.get("error_message"),
            meta={"provider": "google_places"},
        )
        if ok:
            result = data["result"]
            geo = result.get("geometry", {}).get("location", {})
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
    """Geocodifica una dirección de texto usando Geocoding API (sesgado a Colombia)."""
    if not GOOGLE_MAPS_API_KEY:
        logger.warning("[GEOCODE] GOOGLE_MAPS_API_KEY no configurada")
        return None
    if not query:
        return None
    try:
        import requests
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "address": query,
            "region": "CO",
            "components": "country:CO",
            "key": GOOGLE_MAPS_API_KEY,
        }
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        status = data.get("status")
        logger.warning("[GEOCODE] query=%r status=%s", query, status)
        ok = status == "OK" and bool(data.get("results"))
        record_api_usage_event(
            "google_maps",
            "geocode_forward",
            success=ok,
            units=1,
            units_kind="call",
            cost_usd=_google_cost_usd("geocode_forward"),
            http_status=getattr(r, "status_code", None),
            provider_status=status,
            error_message=data.get("error_message"),
            meta={"provider": "google_geocode"},
        )
        if ok:
            result = data["results"][0]
            geo = result.get("geometry", {}).get("location", {})
            fa = result.get("formatted_address")
            logger.warning("[GEOCODE] found: %s lat=%s lng=%s", fa, geo.get("lat"), geo.get("lng"))
            return {
                "lat": geo.get("lat"),
                "lng": geo.get("lng"),
                "formatted_address": fa,
                "place_id": result.get("place_id"),
                "provider": "google_geocode",
            }
        else:
            logger.warning("[GEOCODE] no results: %s", data.get("error_message", ""))
    except Exception as e:
        logger.warning("[GEOCODE] excepcion: %s", e)
    return None


def google_places_text_search(query: str) -> Optional[Dict[str, Any]]:
    """Busca un lugar por texto libre usando Places Text Search API.
    Equivale a escribir en el buscador de Google Maps — encuentra barrios,
    establecimientos y puntos informales que Geocoding no siempre encuentra."""
    if not GOOGLE_MAPS_API_KEY:
        logger.warning("[PLACES] GOOGLE_MAPS_API_KEY no configurada")
        return None
    if not query:
        return None
    try:
        import requests
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            "query": query,
            "region": "CO",
            "location": "4.8133,-75.6961",  # Centro de Pereira (sesgo, no filtro duro)
            "radius": 30000,                 # 30 km cubre Pereira, Dosquebradas, Santa Rosa
            "key": GOOGLE_MAPS_API_KEY,
        }
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        status = data.get("status")
        logger.warning("[PLACES] query=%r status=%s", query, status)
        ok = status == "OK" and bool(data.get("results"))
        record_api_usage_event(
            "google_maps",
            "places_text_search",
            success=ok,
            units=1,
            units_kind="call",
            cost_usd=_google_cost_usd("places_text_search"),
            http_status=getattr(r, "status_code", None),
            provider_status=status,
            error_message=data.get("error_message"),
            meta={"provider": "google_textsearch"},
        )
        if ok:
            result = data["results"][0]
            geo = result.get("geometry", {}).get("location", {})
            fa = result.get("formatted_address") or result.get("name", "")
            logger.warning("[PLACES] found: %s lat=%s lng=%s", fa, geo.get("lat"), geo.get("lng"))
            return {
                "lat": geo.get("lat"),
                "lng": geo.get("lng"),
                "formatted_address": fa,
                "place_id": result.get("place_id"),
                "provider": "google_textsearch",
            }
        else:
            logger.warning("[PLACES] no results: %s", data.get("error_message", ""))
    except Exception as e:
        logger.warning("[PLACES] excepcion: %s", e)
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

        status = data.get("status")
        ok = status == "OK"
        record_api_usage_event(
            "google_maps",
            "distance_matrix_coords",
            success=ok,
            units=1,
            units_kind="call",
            cost_usd=_google_cost_usd("distance_matrix_coords"),
            http_status=getattr(response, "status_code", None),
            provider_status=status,
            error_message=data.get("error_message"),
            meta={"provider": "google_distance_matrix", "mode": "coords"},
        )
        if not ok:
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


def admin_puede_operar(admin_id: int, min_couriers: int = 10, min_allies: int = 5,
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
        "tarifa_parada_adicional": _to_int(get_setting("pricing_tarifa_parada_adicional", "4000"), 4000),
    }


def get_buy_pricing_config():
    """Carga la configuracion de recargos por productos (Compras) desde BD.

    Modelo: los primeros 'free_threshold' productos no tienen recargo.
    Los productos adicionales cobran 'extra_fee' c/u.

    Si buy_free_threshold/buy_extra_fee no existen en BD pero existen claves
    legacy buy_tier*, calcula valores equivalentes minimos como fallback de
    lectura (no hace migracion destructiva).
    """
    raw_threshold = get_setting("buy_free_threshold", None)
    raw_extra_fee = get_setting("buy_extra_fee", None)

    if raw_threshold is None and raw_extra_fee is None:
        # Fallback legacy: si existen las claves del modelo anterior de tres tramos
        tier1_fee_raw = get_setting("buy_tier1_fee", None)
        tier2_fee_raw = get_setting("buy_tier2_fee", None)
        tier3_fee_raw = get_setting("buy_tier3_fee", None)
        if tier1_fee_raw is not None or tier2_fee_raw is not None or tier3_fee_raw is not None:
            # Preferencia: tier2 (tramo intermedio) > tier1 > tier3
            # Sin productos gratis; cada producto tiene recargo desde el primero
            if tier2_fee_raw is not None:
                extra_fee = _to_int(tier2_fee_raw, 700)
            elif tier1_fee_raw is not None:
                extra_fee = _to_int(tier1_fee_raw, 1000)
            else:
                extra_fee = _to_int(tier3_fee_raw, 500)
            return {"free_threshold": 0, "extra_fee": extra_fee}

    return {
        "free_threshold": _to_int(raw_threshold if raw_threshold is not None else "2", 2),
        "extra_fee": _to_int(raw_extra_fee if raw_extra_fee is not None else "1000", 1000),
    }


def calc_buy_products_surcharge(n_products: int, config: dict = None) -> int:
    """
    Calcula el recargo por productos para servicio de Compras.

    Modelo:
    - Primeros 'free_threshold' productos (default 2): sin recargo
    - Productos adicionales: +extra_fee c/u (default $1.000)

    Ejemplo con free_threshold=2, extra_fee=1000:
    - 1-2 productos: $0
    - 3 productos:   $1.000  (1 adicional)
    - 5 productos:   $3.000  (3 adicionales)
    - 10 productos:  $8.000  (8 adicionales)

    Args:
        n_products: Numero total de productos
        config: Dict con configuracion. Si None, carga desde BD.

    Returns:
        Recargo total en pesos
    """
    if n_products <= 0:
        return 0

    if config is None:
        config = get_buy_pricing_config()

    free_threshold = max(0, config.get("free_threshold", 2))
    extra_fee = max(0, config.get("extra_fee", 1000))

    extra_products = max(0, n_products - free_threshold)
    return extra_products * extra_fee


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


def calcular_precio_ruta(total_distance_km: float, num_stops: int, config: dict = None) -> dict:
    """
    Calcula el precio de una ruta multi-parada.

    - distance_fee: precio de la distancia total (fórmula existente de calcular_precio_distancia)
    - additional_stops_fee: (num_stops - 1) * tarifa_parada_adicional (default 4000)
    - total_fee: suma de ambos

    Args:
        total_distance_km: Distancia total de la ruta en km (suma secuencial de segmentos)
        num_stops: Número total de paradas de entrega
        config: Dict de configuración de precios. Si None, carga desde BD.

    Returns:
        dict con: distance_fee, additional_stops_fee, total_fee, total_distance_km, num_stops
    """
    if config is None:
        config = get_pricing_config()
    tarifa_parada_adicional = config.get("tarifa_parada_adicional", 4000)
    distance_fee = calcular_precio_distancia(total_distance_km, config)
    additional_fee = (num_stops - 1) * tarifa_parada_adicional
    return {
        "distance_fee": distance_fee,
        "additional_stops_fee": additional_fee,
        "total_fee": distance_fee + additional_fee,
        "total_distance_km": total_distance_km,
        "num_stops": num_stops,
    }


def calcular_distancia_ruta(pickup_lat, pickup_lng, paradas):
    """
    Calcula la distancia total de una ruta de forma secuencial usando Haversine:
    pickup->stop1 + stop1->stop2 + ...

    Retorna el total en km o None si algún punto carece de GPS.
    """
    if not pickup_lat or not pickup_lng:
        return None
    total = 0.0
    prev_lat, prev_lng = float(pickup_lat), float(pickup_lng)
    for p in paradas:
        lat = p.get("lat")
        lng = p.get("lng")
        if not lat or not lng:
            return None
        total += haversine_road_km(prev_lat, prev_lng, float(lat), float(lng))
        prev_lat, prev_lng = float(lat), float(lng)
    return round(total, 2)


def calcular_distancia_ruta_smart(pickup_lat, pickup_lng, paradas):
    """
    Calcula la distancia total de la ruta segmento a segmento usando la misma
    estrategia de 3 capas que get_smart_distance:
      Capa 1 - Cache: reutiliza distancias ya calculadas (gratis).
      Capa 2 - Google Distance Matrix API: por segmento, con control de cuota.
      Capa 3 - Haversine: fallback si no hay cuota o falla la API.

    Retorna dict {"total_km": float, "used_api": bool} o None si faltan coords.
    """
    if not pickup_lat or not pickup_lng:
        return None
    puntos = [(float(pickup_lat), float(pickup_lng))]
    for p in paradas:
        lat = p.get("lat")
        lng = p.get("lng")
        if not lat or not lng:
            return None
        puntos.append((float(lat), float(lng)))

    total_km = 0.0
    used_api = False

    for i in range(len(puntos) - 1):
        lat1, lng1 = puntos[i]
        lat2, lng2 = puntos[i + 1]

        origin_key = _coords_cache_key(lat1, lng1)
        dest_key = _coords_cache_key(lat2, lng2)

        # Capa 1: Cache
        cached = get_distance_cache(origin_key, dest_key, mode="coords")
        if cached and cached.get("distance_km") is not None:
            total_km += float(cached["distance_km"])
            continue

        # Capa 2: Google Distance Matrix API
        seg_km = None
        if can_call_google_today() and GOOGLE_MAPS_API_KEY:
            seg_km = get_distance_from_api_coords(lat1, lng1, lat2, lng2)
            if seg_km is not None:
                upsert_distance_cache(origin_key, dest_key, mode="coords",
                                      distance_km=seg_km, provider="google_distance_matrix")
                used_api = True

        # Capa 3: Haversine fallback
        if seg_km is None:
            seg_km = round(_haversine_km(lat1, lng1, lat2, lng2) * _distance_factor(), 2)
            upsert_distance_cache(origin_key, dest_key, mode="coords",
                                  distance_km=seg_km, provider="haversine")

        total_km += seg_km

    return {
        "total_km": round(total_km, 2),
        "used_api": used_api,
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

        status = data.get("status")
        ok = status == "OK"
        record_api_usage_event(
            "google_maps",
            "distance_matrix_text",
            success=ok,
            units=1,
            units_kind="call",
            cost_usd=_google_cost_usd("distance_matrix_text"),
            http_status=getattr(response, "status_code", None),
            provider_status=status,
            error_message=data.get("error_message"),
            meta={"provider": "google_distance_matrix", "mode": "text"},
        )
        if not ok:
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

def _is_allowed_city(formatted_address: str) -> bool:
    """True si la direccion corresponde a Pereira, Dosquebradas o Santa Rosa de Cabal."""
    if not formatted_address:
        return False
    import unicodedata
    normalized = unicodedata.normalize("NFD", formatted_address.lower())
    normalized = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    allowed = ("pereira", "dosquebradas", "santa rosa de cabal")
    return any(city in normalized for city in allowed)


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
    try:
        quota_ok = can_call_google_today()
    except Exception:
        quota_ok = False

    if quota_ok and not is_url_like:
        # Cascada de consultas: texto original + sufijos de ciudad
        # Para en el primer resultado valido (economia de cuota).
        # Para mas candidatos usa resolve_location_next().
        _queries = [
            text,
            f"{text}, Pereira, Risaralda, Colombia",
            f"{text}, Dosquebradas, Risaralda, Colombia",
            f"{text}, Santa Rosa de Cabal, Risaralda, Colombia",
        ]
        for _q in _queries:
            geo = google_geocode_forward(_q)
            if geo and geo.get("lat") and geo.get("lng"):
                if _is_allowed_city(geo.get("formatted_address", "")):
                    try:
                        upsert_reference_alias_candidate(
                            raw_text=text,
                            normalized_text=normalized_text,
                            suggested_lat=geo["lat"],
                            suggested_lng=geo["lng"],
                            source="geocode",
                        )
                    except Exception:
                        pass
                    return {
                        "lat": geo["lat"],
                        "lng": geo["lng"],
                        "method": "geocode",
                        "formatted_address": geo.get("formatted_address", ""),
                        "place_id": geo.get("place_id"),
                    }

            try:
                quota_ok2 = can_call_google_today()
            except Exception:
                quota_ok2 = False
            if not quota_ok2:
                break

            places = google_places_text_search(_q)
            if places and places.get("lat") and places.get("lng"):
                if _is_allowed_city(places.get("formatted_address", "")):
                    try:
                        upsert_reference_alias_candidate(
                            raw_text=text,
                            normalized_text=normalized_text,
                            suggested_lat=places["lat"],
                            suggested_lng=places["lng"],
                            source="textsearch",
                        )
                    except Exception:
                        pass
                    return {
                        "lat": places["lat"],
                        "lng": places["lng"],
                        "method": "geocode",
                        "formatted_address": places.get("formatted_address", ""),
                        "place_id": places.get("place_id"),
                    }

    if not is_url_like:
        try:
            upsert_reference_alias_candidate(
                raw_text=text,
                normalized_text=normalized_text,
                source="unresolved",
            )
        except Exception:
            pass
    return None


def resolve_location_next(text: str, seen_ids: list) -> Optional[Dict[str, Any]]:
    """
    Retorna el siguiente candidato de geocoding distinto a los ya mostrados.
    Carga perezosa: solo se llama cuando el usuario rechaza el candidato anterior.
    seen_ids: lista de place_id o 'lat,lng' ya mostrados.
    """
    if not text:
        return None
    text = text.strip()
    if "http" in text.lower():
        return None
    try:
        quota_ok = can_call_google_today()
    except Exception:
        quota_ok = False
    if not quota_ok:
        return None

    _queries = [
        text,
        f"{text}, Pereira, Risaralda, Colombia",
        f"{text}, Dosquebradas, Risaralda, Colombia",
        f"{text}, Santa Rosa de Cabal, Risaralda, Colombia",
    ]
    for _q in _queries:
        geo = google_geocode_forward(_q)
        if geo and geo.get("lat") and geo.get("lng"):
            if _is_allowed_city(geo.get("formatted_address", "")):
                _pid = geo.get("place_id") or f"{geo['lat']},{geo['lng']}"
                if _pid not in seen_ids:
                    return {
                        "lat": geo["lat"],
                        "lng": geo["lng"],
                        "formatted_address": geo.get("formatted_address", ""),
                        "place_id": _pid,
                    }

        try:
            quota_ok2 = can_call_google_today()
        except Exception:
            quota_ok2 = False
        if not quota_ok2:
            break

        places = google_places_text_search(_q)
        if places and places.get("lat") and places.get("lng"):
            if _is_allowed_city(places.get("formatted_address", "")):
                _pid = places.get("place_id") or f"{places['lat']},{places['lng']}"
                if _pid not in seen_ids:
                    return {
                        "lat": places["lat"],
                        "lng": places["lng"],
                        "formatted_address": places.get("formatted_address", ""),
                        "place_id": _pid,
                    }
    return None


# ============================================================
# SISTEMA DE RECARGAS
# ============================================================

def approve_recharge_request(request_id: int, decided_by_admin_id: int) -> Tuple[bool, str]:
    """
    Aprueba una solicitud de recarga.
    - Todos los admins (LOCAL y PLATAFORMA) deben tener saldo suficiente.
    - El saldo se descuenta del admin aprobador y se acredita al destinatario.
    - Registra el movimiento completo en ledger (doble entrada).

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
    elif target_type in ("COURIER", "ALLY"):
        # La validación real del vínculo se ejecuta en el UPDATE por
        # (target_id, admin_id, status='APPROVED') dentro de la transacción.
        # Así evitamos depender del "vínculo más reciente".
        pass
    else:
        return False, f"Tipo de destino desconocido: {target_type}"

    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"

    conn = get_connection()
    cur = conn.cursor()
    try:
        if DB_ENGINE == "sqlite":
            cur.execute("BEGIN IMMEDIATE")

        # Postgres: bloquear fila de solicitud para evitar race condition (approve vs reject
        # concurrente). Re-verifica PENDING dentro de la transacción antes de tocar saldos.
        # SQLite ya está protegido por BEGIN IMMEDIATE.
        for_update = " FOR UPDATE" if DB_ENGINE == "postgres" else ""
        cur.execute(
            "SELECT status FROM recharge_requests WHERE id = " + P + for_update,
            (request_id,),
        )
        row_req = cur.fetchone()
        if not row_req or row_req["status"] != "PENDING":
            conn.rollback()
            return False, "Solicitud ya procesada."

        cur.execute("SELECT balance FROM admins WHERE id = " + P + for_update, (admin_id,))
        row = cur.fetchone()
        current_admin_balance = row["balance"] if row else 0
        if current_admin_balance < amount:
            conn.rollback()
            return False, f"Saldo insuficiente. Tienes ${current_admin_balance:,} y se requieren ${amount:,}."

        cur.execute(
            "UPDATE admins SET balance = balance - " + P + " WHERE id = " + P,
            (amount, admin_id),
        )
        from_type_label = "PLATFORM" if is_platform else "ADMIN"
        cur.execute(
            "INSERT INTO ledger"
            "    (kind, from_type, from_id, to_type, to_id, amount, ref_type, ref_id, note)"
            " VALUES (" + ", ".join([P] * 9) + ")",
            (
                "RECHARGE", from_type_label, admin_id, from_type_label, admin_id, amount,
                "RECHARGE_REQUEST", request_id,
                f"Recarga aprobada por admin_id={decided_by_admin_id} a {target_type} id={target_id}",
            ),
        )

        if target_type == "ADMIN":
            cur.execute(
                "UPDATE admins SET balance = balance + " + P + " WHERE id = " + P,
                (amount, target_id),
            )
            cur.execute(
                "INSERT INTO ledger"
                "    (kind, from_type, from_id, to_type, to_id, amount, ref_type, ref_id, note)"
                " VALUES (" + ", ".join([P] * 9) + ")",
                (
                    "RECHARGE", "PLATFORM", admin_id, "ADMIN", target_id, amount,
                    "RECHARGE_REQUEST", request_id,
                    f"Recarga de admin local aprobada por plataforma admin_id={decided_by_admin_id}",
                ),
            )
        elif target_type == "COURIER":
            if is_platform:
                # Plataforma: acreditar en vínculo directo plataforma-courier (crear si no existe)
                cur.execute(
                    "UPDATE admin_couriers"
                    " SET balance = balance + " + P + ", status = 'APPROVED', updated_at = " + now_sql +
                    " WHERE courier_id = " + P + " AND admin_id = " + P,
                    (amount, target_id, admin_id),
                )
                if cur.rowcount == 0:
                    now_literal = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
                    cur.execute(
                        "INSERT INTO admin_couriers"
                        " (admin_id, courier_id, status, balance, is_active, created_at, updated_at)"
                        " VALUES (" + ", ".join([P] * 5) + ", " + now_literal + ", " + now_literal + ")",
                        (admin_id, target_id, "APPROVED", amount, 1),
                    )
            else:
                # Admin local: acreditar en su vínculo (cualquier status, incluyendo INACTIVE)
                cur.execute(
                    "UPDATE admin_couriers"
                    " SET balance = balance + " + P + ", status = 'APPROVED', updated_at = " + now_sql +
                    " WHERE courier_id = " + P + " AND admin_id = " + P,
                    (amount, target_id, admin_id),
                )
                if cur.rowcount == 0:
                    conn.rollback()
                    return False, "No hay vinculo con este admin para acreditar saldo al courier."
            # Interruptor de ganancias: desactivar todos los otros vinculos del courier
            cur.execute(
                "UPDATE admin_couriers SET status = 'INACTIVE', updated_at = " + now_sql +
                " WHERE courier_id = " + P + " AND admin_id != " + P,
                (target_id, admin_id),
            )
            cur.execute(
                "INSERT INTO ledger"
                "    (kind, from_type, from_id, to_type, to_id, amount, ref_type, ref_id, note)"
                " VALUES (" + ", ".join([P] * 9) + ")",
                (
                    "RECHARGE", "PLATFORM" if is_platform else "ADMIN", admin_id, "COURIER", target_id, amount,
                    "RECHARGE_REQUEST", request_id,
                    f"Recarga aprobada por admin_id={decided_by_admin_id}",
                ),
            )
        elif target_type == "ALLY":
            if is_platform:
                # Plataforma: acreditar en vínculo directo plataforma-aliado (crear si no existe)
                cur.execute(
                    "UPDATE admin_allies"
                    " SET balance = balance + " + P + ", status = 'APPROVED', updated_at = " + now_sql +
                    " WHERE ally_id = " + P + " AND admin_id = " + P,
                    (amount, target_id, admin_id),
                )
                if cur.rowcount == 0:
                    now_literal = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
                    cur.execute(
                        "INSERT INTO admin_allies"
                        " (admin_id, ally_id, status, balance, created_at, updated_at)"
                        " VALUES (" + ", ".join([P] * 4) + ", " + now_literal + ", " + now_literal + ")",
                        (admin_id, target_id, "APPROVED", amount),
                    )
            else:
                # Admin local: acreditar en su vínculo (cualquier status, incluyendo INACTIVE)
                cur.execute(
                    "UPDATE admin_allies"
                    " SET balance = balance + " + P + ", status = 'APPROVED', updated_at = " + now_sql +
                    " WHERE ally_id = " + P + " AND admin_id = " + P,
                    (amount, target_id, admin_id),
                )
                if cur.rowcount == 0:
                    conn.rollback()
                    return False, "No hay vinculo con este admin para acreditar saldo al aliado."
            # Interruptor de ganancias: desactivar todos los otros vinculos del aliado
            cur.execute(
                "UPDATE admin_allies SET status = 'INACTIVE', updated_at = " + now_sql +
                " WHERE ally_id = " + P + " AND admin_id != " + P,
                (target_id, admin_id),
            )
            cur.execute(
                "INSERT INTO ledger"
                "    (kind, from_type, from_id, to_type, to_id, amount, ref_type, ref_id, note)"
                " VALUES (" + ", ".join([P] * 9) + ")",
                (
                    "RECHARGE", "PLATFORM" if is_platform else "ADMIN", admin_id, "ALLY", target_id, amount,
                    "RECHARGE_REQUEST", request_id,
                    f"Recarga aprobada por admin_id={decided_by_admin_id}",
                ),
            )
        else:
            conn.rollback()
            return False, f"Tipo de destino desconocido: {target_type}"

        cur.execute(
            "UPDATE recharge_requests"
            " SET status = 'APPROVED', decided_by_admin_id = " + P + ", decided_at = " + now_sql +
            " WHERE id = " + P + " AND status = 'PENDING'",
            (decided_by_admin_id, request_id),
        )
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

    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE recharge_requests"
            " SET status = 'REJECTED', decided_by_admin_id = " + P + ", decided_at = " + now_sql +
            " WHERE id = " + P + " AND status = 'PENDING'",
            (decided_by_admin_id, request_id),
        )
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
    Cobra tarifa de $300 por servicio al courier/aliado y distribuye el ingreso.
    Distribucion:
    - Si admin es PLATFORM: $300 van a plataforma.
    - Si admin es local: $200 al admin del miembro, $100 a plataforma.
    El admin no paga comision; recibe ingresos por cada servicio de su equipo.
    Retorna: (success, message)
    """
    fee = 300
    admin_share = 200
    platform_share = 100

    platform_admin = get_platform_admin()
    if not platform_admin:
        return False, "Plataforma no configurada."
    platform_id = platform_admin["id"]
    is_platform = (admin_id == platform_id)

    if target_type == "COURIER":
        balance = get_courier_link_balance(target_id, admin_id)
    elif target_type == "ALLY":
        balance = get_ally_link_balance(target_id, admin_id)
    else:
        return False, "Tipo de destino desconocido: {}".format(target_type)

    if balance < fee:
        return False, "Saldo insuficiente. Balance: ${:,}, requerido: ${:,}.".format(balance, fee)

    if target_type == "COURIER":
        update_courier_link_balance(target_id, admin_id, -fee)
    elif target_type == "ALLY":
        update_ally_link_balance(target_id, admin_id, -fee)

    if is_platform:
        # Plataforma gana los $300 completos
        update_admin_balance_with_ledger(
            admin_id=platform_id,
            delta=fee,
            kind="FEE_INCOME",
            note="Ingreso de tarifa de servicio ({} id={})".format(target_type, target_id),
            ref_type=ref_type,
            ref_id=ref_id,
            from_type=target_type,
            from_id=target_id,
        )
    else:
        # Admin local gana $200
        update_admin_balance_with_ledger(
            admin_id=admin_id,
            delta=admin_share,
            kind="FEE_INCOME",
            note="Ingreso de tarifa de servicio ({} id={})".format(target_type, target_id),
            ref_type=ref_type,
            ref_id=ref_id,
            from_type=target_type,
            from_id=target_id,
        )
        # Plataforma gana $100
        update_admin_balance_with_ledger(
            admin_id=platform_id,
            delta=platform_share,
            kind="PLATFORM_FEE",
            note="Comision plataforma por servicio de {} id={}".format(target_type, target_id),
            ref_type=ref_type,
            ref_id=ref_id,
            from_type=target_type,
            from_id=target_id,
        )

    return True, "Tarifa de ${:,} aplicada.".format(fee)


def check_service_fee_available(target_type: str, target_id: int, admin_id: int) -> Tuple[bool, str]:
    """
    Verifica si el miembro tiene saldo suficiente para cobrar el fee ($300), sin cobrar.
    El admin no paga comision (recibe ingresos), por lo que no se valida su saldo aqui.
    Retorna: (can_operate, error_code)
    error_code: 'OK' o 'MEMBER_SIN_SALDO'
    """
    fee = 300

    if target_type == "COURIER":
        balance = get_courier_link_balance(target_id, admin_id)
    elif target_type == "ALLY":
        balance = get_ally_link_balance(target_id, admin_id)
    else:
        return False, "UNKNOWN_TYPE"

    if balance < fee:
        return False, "MEMBER_SIN_SALDO"

    return True, "OK"


def can_courier_activate(courier_id: int) -> Tuple[bool, str]:
    """
    Verifica si el repartidor tiene saldo operativo suficiente para activarse.
    Requiere al menos $300 en admin_couriers.balance (fee minimo por servicio).
    Retorna (puede_activarse, mensaje_error).
    """
    MIN_BALANCE = 300
    admin_id = get_approved_admin_id_for_courier(courier_id)
    if admin_id is None:
        return False, "No tienes un administrador aprobado. Contacta a tu admin."
    balance = get_courier_link_balance(courier_id, admin_id)
    if balance < MIN_BALANCE:
        return False, (
            "No puedes activarte: tu saldo operativo es ${:,}.\n"
            "Necesitas al menos ${:,} para recibir pedidos.\n"
            "Solicita una recarga a tu administrador.".format(balance, MIN_BALANCE)
        )
    return True, "OK"


def ally_get_order_for_incentive(telegram_id: int, order_id: int) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Retorna pedido si pertenece al aliado y está en estado elegible para incentivo.
    """
    user = get_user_by_telegram_id(telegram_id)
    if not user:
        return False, None, "No se encontro tu usuario."

    ally = get_ally_by_user_id(user["id"])
    if not ally:
        return False, None, "No tienes perfil de aliado."

    order = get_order_by_id(order_id)
    if not order:
        return False, None, "Pedido no encontrado."

    if int(order["ally_id"]) != int(ally["id"]):
        return False, None, "No tienes permiso para modificar este pedido."

    if order["status"] not in ("PENDING", "PUBLISHED", "ACCEPTED"):
        return False, None, "Este pedido ya no permite incentivo (estado: {}).".format(order["status"])

    return True, order, "OK"


def ally_increment_order_incentive(telegram_id: int, order_id: int, delta: int) -> Tuple[bool, Optional[Dict[str, Any]], Optional[int], str]:
    """
    Incrementa incentivo adicional del pedido (solo aliado dueño).
    Retorna (ok, updated_order, courier_telegram_id, message).
    """
    ok, order, msg = ally_get_order_for_incentive(telegram_id, order_id)
    if not ok:
        return False, None, None, msg

    if delta is None:
        return False, None, None, "Monto invalido."

    try:
        delta = int(delta)
    except Exception:
        return False, None, None, "Monto invalido."

    if delta <= 0:
        return False, None, None, "El incentivo debe ser mayor a 0."

    if delta > 200000:
        return False, None, None, "El incentivo es demasiado alto."

    add_order_incentive(int(order_id), int(delta))
    updated = get_order_by_id(order_id)

    courier_telegram_id = None
    try:
        courier_id = updated["courier_id"]
        if courier_id:
            courier = get_courier_by_id(courier_id)
            if courier:
                courier_user = get_user_by_id(courier["user_id"])
                if courier_user and courier_user.get("telegram_id"):
                    courier_telegram_id = int(courier_user["telegram_id"])
    except Exception:
        courier_telegram_id = None

    return True, updated, courier_telegram_id, "OK"


def admin_get_order_for_incentive(telegram_id: int, order_id: int) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Retorna pedido si fue creado por el admin y está en estado elegible para incentivo.
    """
    user = get_user_by_telegram_id(telegram_id)
    if not user:
        return False, None, "No se encontro tu usuario."

    admin = get_admin_by_user_id(user["id"])
    if not admin:
        return False, None, "No tienes perfil de administrador."

    order = get_order_by_id(order_id)
    if not order:
        return False, None, "Pedido no encontrado."

    creator_admin_id = order.get("creator_admin_id") if hasattr(order, "get") else order["creator_admin_id"]
    if not creator_admin_id or int(creator_admin_id) != int(admin["id"]):
        return False, None, "No tienes permiso para modificar este pedido."

    if order["status"] not in ("PENDING", "PUBLISHED", "ACCEPTED"):
        return False, None, "Este pedido ya no permite incentivo (estado: {}).".format(order["status"])

    return True, order, "OK"


def admin_increment_order_incentive(telegram_id: int, order_id: int, delta: int) -> Tuple[bool, Optional[Dict[str, Any]], Optional[int], str]:
    """
    Incrementa incentivo adicional del pedido especial (solo admin creador).
    Retorna (ok, updated_order, courier_telegram_id, message).
    """
    ok, order, msg = admin_get_order_for_incentive(telegram_id, order_id)
    if not ok:
        return False, None, None, msg

    if delta is None:
        return False, None, None, "Monto invalido."

    try:
        delta = int(delta)
    except Exception:
        return False, None, None, "Monto invalido."

    if delta <= 0:
        return False, None, None, "El incentivo debe ser mayor a 0."

    if delta > 200000:
        return False, None, None, "El incentivo es demasiado alto."

    add_order_incentive(int(order_id), int(delta))
    updated = get_order_by_id(order_id)

    courier_telegram_id = None
    try:
        courier_id = updated["courier_id"]
        if courier_id:
            courier = get_courier_by_id(courier_id)
            if courier:
                courier_user = get_user_by_id(courier["user_id"])
                if courier_user and courier_user.get("telegram_id"):
                    courier_telegram_id = int(courier_user["telegram_id"])
    except Exception:
        courier_telegram_id = None

    return True, updated, courier_telegram_id, "OK"


def courier_get_earnings_history(telegram_id: int, days: int = 7) -> Tuple[bool, Optional[Dict[str, Any]], list, str]:
    """
    Retorna historial diario de ganancias del courier (según liquidaciones contables).
    """
    courier = get_courier_by_telegram_id(telegram_id)
    if not courier:
        return False, None, [], "No tienes perfil de repartidor."
    rows = get_courier_daily_earnings_history(int(courier["id"]), days=days)
    return True, courier, rows, "OK"


def courier_get_earnings_by_date_key(telegram_id: int, date_key: str) -> Tuple[bool, Optional[Dict[str, Any]], list, str]:
    """
    Retorna detalle de ganancias para una fecha (YYYY-MM-DD) del courier.
    """
    courier = get_courier_by_telegram_id(telegram_id)
    if not courier:
        return False, None, [], "No tienes perfil de repartidor."
    try:
        rows = get_courier_earnings_by_date(int(courier["id"]), date_key)
    except Exception as e:
        return False, courier, [], str(e)
    return True, courier, rows, "OK"


# Nota de alineacion:
# El cobro de fee al courier ya esta implementado en los flujos de entrega de
# order_delivery.py y en la resolucion web de soporte. Si cambia la politica de
# cobro, actualizar esos puntos de integracion y esta nota en el mismo cambio.


def _get_important_alert_config():
    enabled = str(get_setting("important_alerts_enabled", "1") or "1").strip() == "1"
    seconds_raw = str(get_setting("important_alert_seconds", "20,50") or "20,50")
    seconds = []
    for chunk in seconds_raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            sec = int(chunk)
            if sec > 0:
                seconds.append(sec)
        except Exception:
            continue
    if not seconds:
        seconds = [20, 50]
    return {"enabled": enabled, "seconds": seconds}


def es_admin_plataforma(telegram_id: int) -> bool:
    """
    Valida si el usuario es Administrador de Plataforma.
    Verifica que exista en admins con team_code='PLATFORM' y status='APPROVED'.
    """
    admin = get_admin_by_telegram_id(telegram_id)
    if not admin:
        return False

    # Soportar dict o sqlite3.Row
    if isinstance(admin, dict):
        team_code = admin.get("team_code")
        status = admin.get("status")
    else:
        # sqlite3.Row
        team_code = admin["team_code"] if "team_code" in admin.keys() else None
        status = admin["status"] if "status" in admin.keys() else None

    return team_code == "PLATFORM" and status == "APPROVED"


def _get_reference_reviewer(telegram_id: int):
    """
    Retorna contexto de revisor de referencias.
    - Admin Plataforma: siempre habilitado.
    - Admin Local: requiere status APPROVED y permiso APPROVED.
    """
    user = get_user_by_telegram_id(telegram_id)
    if not user:
        return {"ok": False, "message": "No se encontro tu usuario.", "admin_id": None, "is_platform": False}

    admin = get_admin_by_user_id(user["id"])
    if not admin:
        return {"ok": False, "message": "No tienes perfil de administrador.", "admin_id": None, "is_platform": False}

    admin_id = admin["id"]
    admin_status = admin["status"]
    team_code = admin["team_code"]
    is_platform = bool(team_code == "PLATFORM" and admin_status == "APPROVED")

    if is_platform:
        return {"ok": True, "message": "", "admin_id": admin_id, "is_platform": True}

    if admin_status != "APPROVED":
        return {"ok": False, "message": "Tu admin debe estar APPROVED para validar referencias.", "admin_id": admin_id, "is_platform": False}

    if not can_admin_validate_references(admin_id):
        return {"ok": False, "message": "No tienes permiso para validar referencias.", "admin_id": admin_id, "is_platform": False}

    return {"ok": True, "message": "", "admin_id": admin_id, "is_platform": False}


def _get_missing_role_commands(ally, courier, admin_local, es_admin_plataforma_flag=False):
    cmds = []
    if not ally:
        cmds.append("/soy_aliado")
    if not courier:
        cmds.append("/soy_repartidor")
    admin_status = None
    if admin_local:
        admin_status = admin_local.get("status", "PENDING") if isinstance(admin_local, dict) else admin_local["status"]
    if (not admin_local or admin_status == "INACTIVE") and not es_admin_plataforma_flag:
        cmds.append("/soy_admin")
    return cmds


# ---------------------------------------------------------------------------
# Configuración de alertas de oferta
# ---------------------------------------------------------------------------

def get_offer_alerts_config() -> dict:
    """Lee la configuración de alertas de oferta desde la BD."""
    return {
        "reminders_enabled": str(get_setting("offer_reminders_enabled", "1") or "1").strip(),
        "reminder_seconds": str(get_setting("offer_reminder_seconds", "8,16") or "8,16").strip(),
        "voice_enabled": str(get_setting("offer_voice_enabled", "0") or "0").strip(),
        "voice_file_id": (get_setting("offer_voice_file_id", "") or "").strip(),
    }


def save_offer_voice(file_id: str) -> None:
    """Guarda el file_id de voz y activa la alerta de voz."""
    set_setting("offer_voice_file_id", file_id)
    set_setting("offer_voice_enabled", "1")


def set_offer_reminders_enabled(enabled: bool) -> None:
    set_setting("offer_reminders_enabled", "1" if enabled else "0")


def set_offer_reminder_seconds(seconds_list: list) -> None:
    set_setting("offer_reminder_seconds", ",".join(str(n) for n in seconds_list))


def set_offer_voice_enabled(enabled: bool) -> None:
    set_setting("offer_voice_enabled", "1" if enabled else "0")


def clear_offer_voice() -> None:
    """Limpia el file_id de voz y desactiva la alerta de voz."""
    set_setting("offer_voice_file_id", "")
    set_setting("offer_voice_enabled", "0")


def save_pricing_setting(field: str, value_str: str) -> None:
    """Persiste un campo de tarifa.  Los campos de compras usan prefijo 'buy_',
    los de distancia usan prefijo 'pricing_'."""
    if field in ("buy_free_threshold", "buy_extra_fee"):
        import re as _re
        if not _re.fullmatch(r'\d+', (value_str or "").strip()):
            raise ValueError(f"El campo '{field}' debe ser un entero mayor o igual a 0.")
        int_val = int(value_str.strip())
        if int_val < 0:
            raise ValueError(f"El campo '{field}' no puede ser negativo (valor: {int_val}).")
    if field.startswith("buy_"):
        setting_key = field
    else:
        setting_key = f"pricing_{field}"
    set_setting(setting_key, value_str)


def get_admin_panel_balances() -> dict:
    """Retorna saldos consolidados para el panel web administrativo."""
    return get_admin_panel_balances_data()


def get_admin_panel_users() -> list:
    """Retorna el consolidado de usuarios para el panel web administrativo."""
    return get_admin_panel_users_data()


def get_admin_panel_earnings() -> dict:
    """Retorna resumen e historial de ganancias para el panel web administrativo."""
    return get_admin_panel_earnings_data()


def get_dashboard_stats() -> dict:
    """Retorna las metricas agregadas del dashboard web."""
    return get_dashboard_stats_data()


def get_courier_approval_notification_chat_id(courier_id: int):
    """Retorna el chat_id a notificar cuando se aprueba un courier."""
    return get_courier_telegram_id(courier_id)


def get_ally_approval_notification_chat_id(ally_id: int):
    """Retorna el chat_id a notificar cuando se aprueba un aliado."""
    return get_ally_telegram_id(ally_id)


def parse_team_selection_callback(data: str, domain: str):
    """Acepta temporalmente formatos legacy con ':' y estandar con '_'."""
    raw = (data or "").strip()
    modern_prefix = "{}_".format(domain)
    legacy_prefix = "{}:".format(domain)

    if raw.startswith(modern_prefix):
        return raw.split(modern_prefix, 1)[1].strip()
    if raw.startswith(legacy_prefix):
        return raw.split(legacy_prefix, 1)[1].strip()
    return None


def apply_profile_change_request_update(request_row) -> None:
    """Aplica el cambio de perfil aprobado y coordina migraciones de equipo."""
    target_role = request_row["target_role"]
    target_role_id = request_row["target_role_id"]
    field_name = request_row["field_name"]
    new_value = request_row["new_value"]
    new_lat = request_row["new_lat"]
    new_lng = request_row["new_lng"]

    apply_profile_change_request_data(
        target_role=target_role,
        target_role_id=target_role_id,
        field_name=field_name,
        new_value=new_value,
        new_lat=new_lat,
        new_lng=new_lng,
    )

    if field_name != "admin_team_code":
        return

    team_code = (new_value or "").strip().upper()
    admin_row = get_admin_by_team_code(team_code)
    if not admin_row:
        raise ValueError("Admin destino no encontrado para team_code={}".format(team_code))
    if admin_row["status"] != "APPROVED":
        raise ValueError("Admin destino no esta APPROVED.")

    admin_id = admin_row["id"]
    if target_role == "courier":
        upsert_admin_courier_link(admin_id, target_role_id, status="APPROVED", is_active=1)
        deactivate_other_approved_admin_courier_links(target_role_id, admin_id)
    elif target_role == "ally":
        upsert_admin_ally_link(admin_id, target_role_id, status="APPROVED")
        deactivate_other_approved_admin_ally_links(target_role_id, admin_id)


def get_admin_panel_pricing_settings() -> dict:
    """Retorna las claves de pricing expuestas por el panel web."""
    keys = [
        "pricing_precio_0_2km",
        "pricing_precio_2_3km",
        "pricing_base_distance_km",
        "pricing_km_extra_normal",
        "pricing_umbral_km_largo",
        "pricing_km_extra_largo",
    ]
    return {key: get_setting(key) for key in keys}


def update_admin_panel_pricing_settings(payload: dict) -> None:
    """Actualiza solo las claves de pricing permitidas por el panel web."""
    allowed = {
        "pricing_precio_0_2km",
        "pricing_precio_2_3km",
        "pricing_base_distance_km",
        "pricing_km_extra_normal",
        "pricing_umbral_km_largo",
        "pricing_km_extra_largo",
    }
    for key, value in payload.items():
        if key in allowed:
            set_setting(key, str(value))


def cancel_order_from_admin_panel(order_id: int) -> str:
    """Cancela un pedido desde el panel web si todavia no esta finalizado."""
    status = get_order_status_by_id(order_id)
    if status is None:
        raise LookupError("Pedido no encontrado")
    if status in ("DELIVERED", "CANCELLED"):
        raise ValueError(status)
    cancel_order(order_id, "ADMIN")
    return status


def resolve_support_request_from_admin_panel(support_id: int, action: str, admin_db_id: int) -> int:
    """
    Resuelve una solicitud de soporte del panel web manteniendo las mismas reglas
    operativas que ya usa el backend del bot.
    """
    if action not in ("fin", "cancel_courier", "cancel_ally"):
        raise ValueError("Accion invalida")
    if not admin_db_id:
        raise ValueError("admin_db_id requerido")

    req = get_support_request_full(support_id)
    if not req:
        raise LookupError("Solicitud no encontrada")
    if req["status"] != "PENDING":
        raise RuntimeError("Solicitud ya resuelta")

    order_id = req["order_id"]
    courier_id = req["courier_id"]
    if not order_id:
        raise NotImplementedError("Solicitud de ruta no soportada aun desde web")

    order = get_order_by_id(order_id)
    if not order or order["status"] != "PICKED_UP":
        raise RuntimeError("El pedido no esta en estado de entrega")

    if action == "fin":
        ally_id = order["ally_id"]
        ally_admin_link = get_approved_admin_link_for_ally(ally_id) if ally_id else None
        if ally_admin_link:
            apply_service_fee(
                target_type="ALLY",
                target_id=ally_id,
                admin_id=ally_admin_link["admin_id"],
                ref_type="ORDER",
                ref_id=order_id,
            )
        courier_admin_id = get_approved_admin_id_for_courier(courier_id)
        if courier_admin_id:
            apply_service_fee(
                target_type="COURIER",
                target_id=courier_id,
                admin_id=courier_admin_id,
                ref_type="ORDER",
                ref_id=order_id,
            )
        set_order_status(order_id, "DELIVERED", "delivered_at")
        resolve_support_request(support_id, "DELIVERED", admin_db_id)
        return order_id

    if action == "cancel_courier":
        courier_admin_id = get_approved_admin_id_for_courier(courier_id)
        if courier_admin_id:
            apply_service_fee(
                target_type="COURIER",
                target_id=courier_id,
                admin_id=courier_admin_id,
                ref_type="ORDER",
                ref_id=order_id,
            )
        cancel_order(order_id, "ADMIN")
        resolve_support_request(support_id, "CANCELLED_COURIER", admin_db_id)
        return order_id

    ally_id = order["ally_id"]
    ally_admin_link = get_approved_admin_link_for_ally(ally_id) if ally_id else None
    if ally_admin_link:
        apply_service_fee(
            target_type="ALLY",
            target_id=ally_id,
            admin_id=ally_admin_link["admin_id"],
            ref_type="ORDER",
            ref_id=order_id,
        )
    courier_admin_id = get_approved_admin_id_for_courier(courier_id)
    if courier_admin_id:
        apply_service_fee(
            target_type="COURIER",
            target_id=courier_id,
            admin_id=courier_admin_id,
            ref_type="ORDER",
            ref_id=order_id,
        )
    cancel_order(order_id, "ADMIN")
    resolve_support_request(support_id, "CANCELLED_ALLY", admin_db_id)
    return order_id


# ---------------------------------------------------------------------------
# Candidatos de referencias (alias de ubicación)
# ---------------------------------------------------------------------------

def get_pending_reference_candidates(offset: int = 0, limit: int = 10) -> list:
    """Devuelve la lista de candidatos de referencia en estado PENDING."""
    return list_reference_alias_candidates(status="PENDING", limit=limit, offset=offset)


def get_reference_candidate(candidate_id: int):
    """Devuelve un candidato de referencia por su id, o None."""
    return get_reference_alias_candidate_by_id(candidate_id)


def review_reference_candidate(candidate_id: int, new_status: str,
                                reviewed_by_admin_id, note: str = ""):
    """Aprueba o rechaza un candidato de referencia.  Devuelve (ok, msg)."""
    return review_reference_alias_candidate(
        candidate_id,
        new_status,
        reviewed_by_admin_id=reviewed_by_admin_id,
        note=note,
    )


def set_reference_candidate_coords(candidate_id: int, lat: float, lng: float) -> bool:
    """Asigna coordenadas a un candidato de referencia.  Devuelve True si OK."""
    return set_reference_alias_candidate_coords(candidate_id, lat, lng, source="manual_pin")


def get_user_db_id_from_update(update) -> int:
    """Retorna el users.id interno del usuario de Telegram, creándolo si no existe."""
    user_tg = update.effective_user
    user_row = ensure_user(user_tg.id, user_tg.username)
    return user_row["id"]


def can_use_cotizador(telegram_id: int):
    """
    Permite usar /cotizar solo a usuarios registrados (ally/courier/admin)
    y con rol en estado APPROVED.
    Retorna (ok, message).
    """
    user = get_user_by_telegram_id(telegram_id)
    if not user:
        return False, "Para usar /cotizar primero debes iniciar el bot con /start."

    user_id = user["id"]

    admin = get_admin_by_user_id(user_id)
    if admin and str(admin.get("status") or "").upper() == "APPROVED":
        return True, "OK"

    ally = get_ally_by_user_id(user_id)
    if ally and str(ally.get("status") or "").upper() == "APPROVED":
        return True, "OK"

    courier = get_courier_by_user_id(user_id)
    if courier and str(courier.get("status") or "").upper() == "APPROVED":
        return True, "OK"

    if admin or ally or courier:
        return False, "Tu registro aun no esta aprobado. Cuando estes en estado APPROVED podras usar /cotizar."

    return False, "Para usar /cotizar debes estar registrado como aliado, repartidor o admin y estar en estado APPROVED."


# ---------------------------------------------------------------------------
# Helpers de estado de courier (evitan confusión entre status y availability_status)
# ---------------------------------------------------------------------------

def courier_role_is_approved(courier) -> bool:
    """True si el courier tiene su ROL aprobado (couriers.status == 'APPROVED').
    Usar para saber si el courier fue validado y puede operar en el sistema."""
    if not courier:
        return False
    return _row_value(courier, "status", 10) == "APPROVED"


def courier_is_operational(courier) -> bool:
    """True si el courier está disponible en turno (couriers.availability_status == 'APPROVED').
    Usar para saber si el courier está activo en el momento actual para recibir pedidos.
    Requiere que courier_role_is_approved() también sea True para que tenga sentido."""
    if not courier:
        return False
    return _row_value(courier, "availability_status", 20) == "APPROVED"
