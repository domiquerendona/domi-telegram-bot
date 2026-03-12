# Importa utilidades de FastAPI para definir rutas, dependencias y errores HTTP
from fastapi import APIRouter, Depends, HTTPException
from typing import List

# Guard que valida si el usuario autenticado tiene permisos de administrador
from web.auth.guards import is_admin

# Servicios de administración que modifican el estado del usuario
from web.admin.services import approve_user, reject_user, deactivate_user

# Función del repository para obtener usuarios por ID
from web.users.repository import get_user_by_id

# Dependencia que obtiene el usuario autenticado (mock o JWT en el futuro)
from web.auth.dependencies import get_current_user

# Schemas de respuesta
from web.schemas.user import UserResponse, AdminResponse, CourierResponse, AllyResponse, OrderResponse

# Funciones de acceso a datos
from db import (
    get_all_online_couriers, get_active_orders_without_courier,
    get_all_admins, update_admin_status_by_id,
    get_all_couriers, update_courier_status_by_id,
    get_all_allies, update_ally_status_by_id,
    get_all_orders, get_connection, cancel_order,
    get_all_pending_support_requests, get_support_request_full,
    resolve_support_request, get_order_by_id, set_order_status,
    get_approved_admin_link_for_ally, get_approved_admin_id_for_courier,
)
from services import apply_service_fee


# Router para endpoints administrativos
# Todos los endpoints aquí tendrán el prefijo /admin
router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/users/{user_id}/approve", response_model=UserResponse)
def approve_user_endpoint(
    user_id: int,
    admin=Depends(get_current_user)
):
    """
    Endpoint para aprobar un usuario por su ID.
    Solo accesible por usuarios con rol administrador.
    """

    # Verifica que el usuario autenticado tenga permisos administrativos
    if not is_admin(admin):
        raise HTTPException(status_code=403, detail="No autorizado")

    # Obtiene el usuario que se desea aprobar
    user = get_user_by_id(user_id)

    # Si el usuario no existe, retorna error 404
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Ejecuta la acción de aprobación (cambia el estado a APPROVED)
    approve_user(user)

    # Retorna el usuario aprobado serializado con UserResponse
    return user


@router.get("/admins", response_model=list[AdminResponse])
def list_admins(admin=Depends(get_current_user)):
    """Lista todos los administradores locales. Solo accesible por el admin de plataforma."""
    if not is_admin(admin):
        raise HTTPException(status_code=403, detail="No autorizado")
    rows = get_all_admins()
    result = []
    for r in rows:
        result.append({
            "id": r["id"] if hasattr(r, "__getitem__") else r[0],
            "full_name": r["full_name"] if hasattr(r, "__getitem__") else r[2],
            "phone": r["phone"] if hasattr(r, "__getitem__") else r[3],
            "city": r["city"] if hasattr(r, "__getitem__") else r[4],
            "barrio": r["barrio"] if hasattr(r, "__getitem__") else r[5],
            "status": r["status"] if hasattr(r, "__getitem__") else r[6],
            "team_name": r["team_name"] if hasattr(r, "__getitem__") else r[8],
            "document_number": r["document_number"] if hasattr(r, "__getitem__") else r[9],
            "created_at": str(r["created_at"]) if hasattr(r, "__getitem__") else str(r[7]),
        })
    return result


@router.post("/admins/{admin_id}/approve")
def approve_admin_endpoint(admin_id: int, admin=Depends(get_current_user)):
    """Aprueba un administrador local pendiente."""
    if not is_admin(admin):
        raise HTTPException(status_code=403, detail="No autorizado")
    update_admin_status_by_id(admin_id, "APPROVED")
    return {"ok": True}


@router.post("/admins/{admin_id}/reject")
def reject_admin_endpoint(admin_id: int, admin=Depends(get_current_user)):
    """Rechaza un administrador local."""
    if not is_admin(admin):
        raise HTTPException(status_code=403, detail="No autorizado")
    update_admin_status_by_id(admin_id, "REJECTED")
    return {"ok": True}


@router.post("/admins/{admin_id}/deactivate")
def deactivate_admin_endpoint(admin_id: int, admin=Depends(get_current_user)):
    """Inactiva un administrador local aprobado."""
    if not is_admin(admin):
        raise HTTPException(status_code=403, detail="No autorizado")
    update_admin_status_by_id(admin_id, "INACTIVE")
    return {"ok": True}


@router.post("/admins/{admin_id}/reactivate")
def reactivate_admin_endpoint(admin_id: int, admin=Depends(get_current_user)):
    """Reactiva un administrador local inactivo."""
    if not is_admin(admin):
        raise HTTPException(status_code=403, detail="No autorizado")
    update_admin_status_by_id(admin_id, "APPROVED")
    return {"ok": True}


@router.get("/couriers", response_model=list[CourierResponse])
def list_couriers(admin=Depends(get_current_user)):
    """Lista todos los repartidores."""
    if not is_admin(admin):
        raise HTTPException(status_code=403, detail="No autorizado")
    rows = get_all_couriers()
    return [{
        "id": r["id"], "full_name": r["full_name"], "phone": r["phone"],
        "city": r["city"], "barrio": r["barrio"], "status": r["status"],
        "id_number": r["id_number"] or "", "plate": r["plate"] or "",
        "bike_type": r["bike_type"] or "",
    } for r in rows]


@router.post("/couriers/{courier_id}/approve")
def approve_courier(courier_id: int, admin=Depends(get_current_user)):
    if not is_admin(admin): raise HTTPException(status_code=403, detail="No autorizado")
    update_courier_status_by_id(courier_id, "APPROVED")
    return {"ok": True}


@router.post("/couriers/{courier_id}/reject")
def reject_courier(courier_id: int, admin=Depends(get_current_user)):
    if not is_admin(admin): raise HTTPException(status_code=403, detail="No autorizado")
    update_courier_status_by_id(courier_id, "REJECTED")
    return {"ok": True}


@router.post("/couriers/{courier_id}/deactivate")
def deactivate_courier(courier_id: int, admin=Depends(get_current_user)):
    if not is_admin(admin): raise HTTPException(status_code=403, detail="No autorizado")
    update_courier_status_by_id(courier_id, "INACTIVE")
    return {"ok": True}


@router.post("/couriers/{courier_id}/reactivate")
def reactivate_courier(courier_id: int, admin=Depends(get_current_user)):
    if not is_admin(admin): raise HTTPException(status_code=403, detail="No autorizado")
    update_courier_status_by_id(courier_id, "APPROVED")
    return {"ok": True}


@router.get("/allies", response_model=list[AllyResponse])
def list_allies(admin=Depends(get_current_user)):
    """Lista todos los aliados."""
    if not is_admin(admin):
        raise HTTPException(status_code=403, detail="No autorizado")
    rows = get_all_allies()
    return [{
        "id": r["id"], "business_name": r["business_name"], "owner_name": r["owner_name"],
        "phone": r["phone"], "city": r["city"], "barrio": r["barrio"],
        "status": r["status"], "address": r["address"] or "",
    } for r in rows]


@router.post("/allies/{ally_id}/approve")
def approve_ally(ally_id: int, admin=Depends(get_current_user)):
    if not is_admin(admin): raise HTTPException(status_code=403, detail="No autorizado")
    update_ally_status_by_id(ally_id, "APPROVED")
    return {"ok": True}


@router.post("/allies/{ally_id}/reject")
def reject_ally(ally_id: int, admin=Depends(get_current_user)):
    if not is_admin(admin): raise HTTPException(status_code=403, detail="No autorizado")
    update_ally_status_by_id(ally_id, "REJECTED")
    return {"ok": True}


@router.post("/allies/{ally_id}/deactivate")
def deactivate_ally(ally_id: int, admin=Depends(get_current_user)):
    if not is_admin(admin): raise HTTPException(status_code=403, detail="No autorizado")
    update_ally_status_by_id(ally_id, "INACTIVE")
    return {"ok": True}


@router.post("/allies/{ally_id}/reactivate")
def reactivate_ally(ally_id: int, admin=Depends(get_current_user)):
    if not is_admin(admin): raise HTTPException(status_code=403, detail="No autorizado")
    update_ally_status_by_id(ally_id, "APPROVED")
    return {"ok": True}


@router.get("/couriers/active-locations")
def get_active_courier_locations(admin=Depends(get_current_user)):
    """
    Retorna todos los repartidores con ubicacion en vivo activa (ONLINE).
    Incluye lat/lng, nombre, equipo y timestamp de ultima actualizacion.
    Solo accesible por administradores.
    """
    if not is_admin(admin):
        raise HTTPException(status_code=403, detail="No autorizado")

    couriers = get_all_online_couriers()
    result = []
    for c in couriers:
        result.append({
            "courier_id": c["courier_id"],
            "full_name": c["full_name"],
            "telegram_id": c["telegram_id"],
            "phone": c["phone"],
            "lat": float(c["live_lat"]) if c["live_lat"] else None,
            "lng": float(c["live_lng"]) if c["live_lng"] else None,
            "admin_city": c["admin_city"],
            "admin_id": c["admin_id"],
            "last_updated": str(c["live_location_updated_at"]) if c["live_location_updated_at"] else None,
        })
    return result


@router.get("/orders/unassigned")
def get_unassigned_orders(admin=Depends(get_current_user)):
    """
    Retorna pedidos activos sin courier asignado que tienen coordenadas de pickup.
    Usado por el mapa del panel para mostrar pedidos en espera.
    Solo accesible por administradores.
    """
    if not is_admin(admin):
        raise HTTPException(status_code=403, detail="No autorizado")

    orders = get_active_orders_without_courier(limit=30)
    result = []
    for o in orders:
        result.append({
            "order_id": o["id"],
            "status": o["status"],
            "pickup_address": o["pickup_address"],
            "pickup_lat": float(o["pickup_lat"]) if o["pickup_lat"] else None,
            "pickup_lng": float(o["pickup_lng"]) if o["pickup_lng"] else None,
            "customer_name": o["customer_name"],
            "ally_name": o["ally_name"],
            "created_at": str(o["created_at"]) if o["created_at"] else None,
        })
    return result


@router.get("/orders", response_model=list[OrderResponse])
def list_orders(status: str = None, admin=Depends(get_current_user)):
    """Lista todos los pedidos del sistema con nombre de courier y aliado."""
    if not is_admin(admin):
        raise HTTPException(status_code=403, detail="No autorizado")

    # Construir lookups de nombres usando funciones que ya funcionan
    courier_names = {r["id"]: r["full_name"] for r in get_all_couriers()}
    ally_names = {r["id"]: r["business_name"] for r in get_all_allies()}

    rows = get_all_orders(status_filter=status, limit=200)
    result = []
    for o in rows:
        result.append({
            "id": o["id"],
            "status": o["status"],
            "customer_name": o["customer_name"],
            "customer_phone": o["customer_phone"],
            "customer_address": o["customer_address"],
            "customer_city": o["customer_city"],
            "customer_barrio": o["customer_barrio"],
            "total_fee": o["total_fee"] or 0,
            "additional_incentive": o["additional_incentive"] or 0,
            "courier_name": courier_names.get(o["courier_id"], "") if o["courier_id"] else "",
            "ally_name": ally_names.get(o["ally_id"], "") if o["ally_id"] else "",
            "created_at": str(o["created_at"]) if o["created_at"] else "",
            "delivered_at": str(o["delivered_at"]) if o["delivered_at"] else "",
            "canceled_at": str(o["canceled_at"]) if o["canceled_at"] else "",
        })
    return result


@router.get("/saldos")
def get_saldos(admin=Depends(get_current_user)):
    """Retorna saldos de admins, repartidores y aliados."""
    if not is_admin(admin):
        raise HTTPException(status_code=403, detail="No autorizado")

    conn = get_connection()
    cur = conn.cursor()

    # Saldos de administradores
    cur.execute("""
        SELECT a.id, a.full_name, a.balance, a.status, a.city
        FROM admins a
        ORDER BY a.balance DESC
    """)
    admins_rows = cur.fetchall()

    # Saldos de repartidores (del vínculo activo)
    cur.execute("""
        SELECT c.id, c.full_name, ac.balance, ac.status AS link_status,
               c.status AS courier_status, c.city, a.full_name AS admin_name
        FROM admin_couriers ac
        JOIN couriers c ON c.id = ac.courier_id
        JOIN admins a ON a.id = ac.admin_id
        WHERE ac.status = 'APPROVED'
        ORDER BY ac.balance DESC
    """)
    couriers_rows = cur.fetchall()

    # Saldos de aliados (del vínculo activo)
    cur.execute("""
        SELECT al.id, al.business_name, aa.balance, aa.status AS link_status,
               al.status AS ally_status, al.city, a.full_name AS admin_name
        FROM admin_allies aa
        JOIN allies al ON al.id = aa.ally_id
        JOIN admins a ON a.id = aa.admin_id
        WHERE aa.status = 'APPROVED'
        ORDER BY aa.balance DESC
    """)
    allies_rows = cur.fetchall()
    conn.close()

    def row_val(row, key, idx):
        try:
            return row[key]
        except (KeyError, TypeError, IndexError):
            return row[idx]

    return {
        "admins": [
            {
                "id": row_val(r, "id", 0),
                "nombre": row_val(r, "full_name", 1),
                "balance": row_val(r, "balance", 2) or 0,
                "status": row_val(r, "status", 3),
                "ciudad": row_val(r, "city", 4) or "",
            }
            for r in admins_rows
        ],
        "couriers": [
            {
                "id": row_val(r, "id", 0),
                "nombre": row_val(r, "full_name", 1),
                "balance": row_val(r, "balance", 2) or 0,
                "status": row_val(r, "courier_status", 4),
                "ciudad": row_val(r, "city", 5) or "",
                "admin_nombre": row_val(r, "admin_name", 6) or "",
            }
            for r in couriers_rows
        ],
        "aliados": [
            {
                "id": row_val(r, "id", 0),
                "nombre": row_val(r, "business_name", 1),
                "balance": row_val(r, "balance", 2) or 0,
                "status": row_val(r, "ally_status", 4),
                "ciudad": row_val(r, "city", 5) or "",
                "admin_nombre": row_val(r, "admin_name", 6) or "",
            }
            for r in allies_rows
        ],
    }


@router.get("/users")
def list_all_users(admin=Depends(get_current_user)):
    """Lista todos los usuarios del sistema con su perfil de rol."""
    if not is_admin(admin):
        raise HTTPException(status_code=403, detail="No autorizado")

    conn = get_connection()
    cur = conn.cursor()

    # Query 1: usuarios Telegram con perfil de rol
    cur.execute("""
        SELECT
            u.id, u.telegram_id, u.username, u.created_at,
            COALESCE(a.full_name, c.full_name, al.business_name, u.username, '') AS nombre,
            COALESCE(a.phone, c.phone, al.phone, '')   AS phone,
            COALESCE(a.city,  c.city,  al.city,  '')   AS ciudad,
            COALESCE(a.status, c.status, al.status, '') AS status,
            CASE
                WHEN a.id IS NOT NULL AND (a.team_name = 'PLATAFORMA' OR u.role IN ('PLATFORM_ADMIN','ADMIN_PLATFORM'))
                    THEN 'PLATFORM_ADMIN'
                WHEN a.id IS NOT NULL THEN 'ADMIN_LOCAL'
                WHEN c.id IS NOT NULL THEN 'COURIER'
                WHEN al.id IS NOT NULL THEN 'ALLY'
                WHEN u.role IN ('PLATFORM_ADMIN','ADMIN_PLATFORM') THEN 'PLATFORM_ADMIN'
                ELSE COALESCE(u.role, '')
            END AS rol_inferido
        FROM users u
        LEFT JOIN admins  a  ON a.user_id = u.id AND a.is_deleted = 0
        LEFT JOIN couriers c ON c.user_id = u.id
        LEFT JOIN allies  al ON al.user_id = u.id AND (al.is_deleted IS NULL OR al.is_deleted = 0)
        ORDER BY u.id DESC
    """)
    telegram_users = cur.fetchall()

    # Query 2: todos los couriers
    cur.execute("SELECT id, full_name, phone, city, status, created_at FROM couriers ORDER BY id")
    all_couriers = cur.fetchall()

    # Query 3: todos los aliados
    cur.execute("SELECT id, business_name, phone, city, status, created_at FROM allies WHERE is_deleted IS NULL OR is_deleted = 0 ORDER BY id")
    all_allies = cur.fetchall()
    conn.close()

    def rv(row, key, idx, default=""):
        try:
            v = row[key]
            return v if v is not None else default
        except (KeyError, TypeError, IndexError):
            try:
                v = row[idx]
                return v if v is not None else default
            except Exception:
                return default

    result = []

    # Usuarios Telegram (admins, couriers/aliados con cuenta)
    for r in telegram_users:
        result.append({
            "id": rv(r, "id", 0, 0),
            "telegram_id": rv(r, "telegram_id", 1, 0),
            "username": rv(r, "username", 2) or "",
            "role": rv(r, "rol_inferido", 8) or "",
            "created_at": str(rv(r, "created_at", 3)) or "",
            "nombre": rv(r, "nombre", 4) or "",
            "phone": rv(r, "phone", 5) or "",
            "ciudad": rv(r, "ciudad", 6) or "",
            "status": rv(r, "status", 7) or "",
        })

    # IDs de couriers/aliados ya incluidos vía users
    courier_ids_seen = {rv(r, "id", 0, 0) for r in telegram_users if rv(r, "rol_inferido", 8) == "COURIER"}
    ally_ids_seen = {rv(r, "id", 0, 0) for r in telegram_users if rv(r, "rol_inferido", 8) == "ALLY"}

    for c in all_couriers:
        cid = rv(c, "id", 0, 0)
        if cid not in courier_ids_seen:
            result.append({
                "id": cid,
                "telegram_id": 0,
                "username": "",
                "role": "COURIER",
                "created_at": str(rv(c, "created_at", 5)) or "",
                "nombre": rv(c, "full_name", 1) or "",
                "phone": rv(c, "phone", 2) or "",
                "ciudad": rv(c, "city", 3) or "",
                "status": rv(c, "status", 4) or "",
            })

    for a in all_allies:
        aid = rv(a, "id", 0, 0)
        if aid not in ally_ids_seen:
            result.append({
                "id": aid,
                "telegram_id": 0,
                "username": "",
                "role": "ALLY",
                "created_at": str(rv(a, "created_at", 5)) or "",
                "nombre": rv(a, "business_name", 1) or "",
                "phone": rv(a, "phone", 2) or "",
                "ciudad": rv(a, "city", 3) or "",
                "status": rv(a, "status", 4) or "",
            })

    return result


@router.get("/ganancias")
def get_ganancias(admin=Depends(get_current_user)):
    """Retorna resumen de ganancias del sistema a partir del ledger."""
    if not is_admin(admin):
        raise HTTPException(status_code=403, detail="No autorizado")

    conn = get_connection()
    cur = conn.cursor()

    # Resumen por periodo: hoy / esta semana / este mes
    cur.execute("""
        SELECT
            SUM(CASE WHEN date(created_at) = date('now') THEN amount ELSE 0 END) AS hoy,
            SUM(CASE WHEN created_at >= date('now', 'weekday 0', '-7 days') THEN amount ELSE 0 END) AS semana,
            SUM(CASE WHEN strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now') THEN amount ELSE 0 END) AS mes,
            SUM(amount) AS total
        FROM ledger
        WHERE kind IN ('FEE_INCOME', 'PLATFORM_FEE')
    """)
    resumen_row = cur.fetchone()

    # Ganancias por admin (todos los tiempos)
    cur.execute("""
        SELECT a.full_name, SUM(l.amount) AS total
        FROM ledger l
        JOIN admins a ON a.id = l.to_id
        WHERE l.kind IN ('FEE_INCOME', 'PLATFORM_FEE') AND l.to_type = 'ADMIN'
        GROUP BY l.to_id, a.full_name
        ORDER BY total DESC
    """)
    por_admin_rows = cur.fetchall()

    # Historial reciente (últimas 50 entradas de ganancias)
    cur.execute("""
        SELECT l.id, l.kind, l.amount, l.from_type, l.from_id, l.note, l.created_at,
               a.full_name AS admin_nombre
        FROM ledger l
        LEFT JOIN admins a ON a.id = l.to_id AND l.to_type = 'ADMIN'
        WHERE l.kind IN ('FEE_INCOME', 'PLATFORM_FEE', 'INCOME')
        ORDER BY l.created_at DESC
        LIMIT 50
    """)
    historial_rows = cur.fetchall()
    conn.close()

    def rv(row, key, idx, default=0):
        try:
            v = row[key]
            return v if v is not None else default
        except (KeyError, TypeError, IndexError):
            try:
                v = row[idx]
                return v if v is not None else default
            except Exception:
                return default

    return {
        "resumen": {
            "hoy": rv(resumen_row, "hoy", 0) or 0,
            "semana": rv(resumen_row, "semana", 1) or 0,
            "mes": rv(resumen_row, "mes", 2) or 0,
            "total": rv(resumen_row, "total", 3) or 0,
        },
        "por_admin": [
            {
                "nombre": rv(r, "full_name", 0, ""),
                "total": rv(r, "total", 1) or 0,
            }
            for r in por_admin_rows
        ],
        "historial": [
            {
                "id": rv(r, "id", 0),
                "kind": rv(r, "kind", 1, ""),
                "amount": rv(r, "amount", 2) or 0,
                "from_type": rv(r, "from_type", 3, ""),
                "note": rv(r, "note", 5, "") or "",
                "created_at": str(rv(r, "created_at", 6, "")) or "",
                "admin_nombre": rv(r, "admin_nombre", 7, "") or "",
            }
            for r in historial_rows
        ],
    }


@router.post("/orders/{order_id}/cancel")
def cancel_order_endpoint(order_id: int, admin=Depends(get_current_user)):
    """Cancela un pedido que aún no ha sido entregado."""
    if not is_admin(admin):
        raise HTTPException(status_code=403, detail="No autorizado")

    conn = get_connection()
    cur = conn.cursor()
    from db import P
    cur.execute(f"SELECT status FROM orders WHERE id = {P}", (order_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    status = row[0] if not hasattr(row, '__getitem__') else row["status"]
    if status in ("DELIVERED", "CANCELLED"):
        raise HTTPException(status_code=400, detail=f"El pedido ya está en estado {status}")

    cancel_order(order_id, "ADMIN")
    return {"ok": True, "order_id": order_id}


@router.get("/settings/pricing")
def get_pricing_settings(admin=Depends(get_current_user)):
    """Retorna las tarifas de precios configuradas en settings."""
    if not is_admin(admin):
        raise HTTPException(status_code=403, detail="No autorizado")
    from db import get_setting
    keys = [
        "pricing_precio_0_2km",
        "pricing_precio_2_3km",
        "pricing_base_distance_km",
        "pricing_km_extra_normal",
        "pricing_umbral_km_largo",
        "pricing_km_extra_largo",
    ]
    return {k: get_setting(k) for k in keys}


@router.post("/settings/pricing")
def update_pricing_settings(payload: dict, admin=Depends(get_current_user)):
    """Actualiza las tarifas de precios en settings."""
    if not is_admin(admin):
        raise HTTPException(status_code=403, detail="No autorizado")
    from db import set_setting
    allowed = {
        "pricing_precio_0_2km",
        "pricing_precio_2_3km",
        "pricing_base_distance_km",
        "pricing_km_extra_normal",
        "pricing_umbral_km_largo",
        "pricing_km_extra_largo",
    }
    for k, v in payload.items():
        if k in allowed:
            set_setting(k, str(v))
    return {"ok": True}


# ---------------------------------------------------------------------------
# Solicitudes de ayuda — pin mal ubicado
# ---------------------------------------------------------------------------

@router.get("/support-requests")
def list_support_requests(admin=Depends(get_current_user)):
    """Lista todas las solicitudes de ayuda pendientes con datos de courier y pedido."""
    if not is_admin(admin):
        raise HTTPException(status_code=403, detail="No autorizado")
    rows = get_all_pending_support_requests()
    return rows


@router.get("/support-requests/{support_id}")
def get_support_request(support_id: int, admin=Depends(get_current_user)):
    """Retorna detalle completo de una solicitud de ayuda."""
    if not is_admin(admin):
        raise HTTPException(status_code=403, detail="No autorizado")
    req = get_support_request_full(support_id)
    if not req:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    return req


@router.post("/support-requests/{support_id}/resolve")
def resolve_support_request_endpoint(support_id: int, payload: dict, admin=Depends(get_current_user)):
    """
    Resuelve una solicitud de ayuda desde el panel web.
    payload: { "action": "fin" | "cancel_courier" | "cancel_ally", "admin_db_id": int }
    Aplica fees en BD. No envía notificaciones Telegram (canal bot).
    """
    if not is_admin(admin):
        raise HTTPException(status_code=403, detail="No autorizado")

    action = payload.get("action")
    admin_db_id = payload.get("admin_db_id")
    if action not in ("fin", "cancel_courier", "cancel_ally"):
        raise HTTPException(status_code=400, detail="Accion invalida")
    if not admin_db_id:
        raise HTTPException(status_code=400, detail="admin_db_id requerido")

    req = get_support_request_full(support_id)
    if not req:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    if req["status"] != "PENDING":
        raise HTTPException(status_code=409, detail="Esta solicitud ya fue resuelta")

    order_id = req["order_id"]
    courier_id = req["courier_id"]

    if not order_id:
        raise HTTPException(status_code=400, detail="Solicitud de ruta no soportada aun desde web")

    order = get_order_by_id(order_id)
    if not order or order["status"] != "PICKED_UP":
        raise HTTPException(status_code=409, detail="El pedido no esta en estado de entrega")

    if action == "fin":
        # Aplicar fees normales y marcar DELIVERED
        ally_id = order["ally_id"]
        ally_admin_link = get_approved_admin_link_for_ally(ally_id) if ally_id else None
        if ally_admin_link:
            apply_service_fee(
                target_type="ALLY", target_id=ally_id,
                admin_id=ally_admin_link["admin_id"],
                ref_type="ORDER", ref_id=order_id,
            )
        courier_admin_id = get_approved_admin_id_for_courier(courier_id)
        if courier_admin_id:
            apply_service_fee(
                target_type="COURIER", target_id=courier_id,
                admin_id=courier_admin_id,
                ref_type="ORDER", ref_id=order_id,
            )
        set_order_status(order_id, "DELIVERED", "delivered_at")
        resolve_support_request(support_id, "DELIVERED", admin_db_id)

    elif action == "cancel_courier":
        # Solo courier paga $300
        courier_admin_id = get_approved_admin_id_for_courier(courier_id)
        if courier_admin_id:
            apply_service_fee(
                target_type="COURIER", target_id=courier_id,
                admin_id=courier_admin_id,
                ref_type="ORDER", ref_id=order_id,
            )
        cancel_order(order_id, "ADMIN")
        resolve_support_request(support_id, "CANCELLED_COURIER", admin_db_id)

    elif action == "cancel_ally":
        # Ambos pagan $300
        ally_id = order["ally_id"]
        ally_admin_link = get_approved_admin_link_for_ally(ally_id) if ally_id else None
        if ally_admin_link:
            apply_service_fee(
                target_type="ALLY", target_id=ally_id,
                admin_id=ally_admin_link["admin_id"],
                ref_type="ORDER", ref_id=order_id,
            )
        courier_admin_id = get_approved_admin_id_for_courier(courier_id)
        if courier_admin_id:
            apply_service_fee(
                target_type="COURIER", target_id=courier_id,
                admin_id=courier_admin_id,
                ref_type="ORDER", ref_id=order_id,
            )
        cancel_order(order_id, "ADMIN")
        resolve_support_request(support_id, "CANCELLED_ALLY", admin_db_id)

    return {"ok": True, "action": action, "order_id": order_id}
