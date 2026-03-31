# Importa utilidades de FastAPI para definir rutas, dependencias y errores HTTP
from fastapi import APIRouter, Depends, HTTPException
from typing import List

# Guards de autorización
from web.auth.guards import require_panel_admin

# Servicios de administración que modifican el estado del usuario
from web.admin.services import approve_user, reject_user, deactivate_user

# Función del repository para obtener usuarios por ID
from web.users.repository import get_user_by_id, list_users as list_web_panel_users

# Dependencias de autenticación y permisos
from web.auth.dependencies import get_current_user, require_permission
from web.users.roles import Permission
from web.users.models import UserRole


def _scoped_admin_id(current_user):
    """Retorna admin_id si el usuario es ADMIN_LOCAL, None si es PLATFORM_ADMIN."""
    if current_user.role == UserRole.ADMIN_LOCAL:
        return current_user.admin_id
    return None

# Schemas de respuesta
from web.schemas.user import UserResponse, AdminResponse, CourierResponse, AllyResponse, OrderResponse

# Funciones de acceso a datos y coordinacion de negocio
from services import (
    get_all_online_couriers, get_active_orders_without_courier,
    get_all_admins, update_admin_status_by_id,
    get_all_couriers, update_courier_status_by_id,
    get_all_allies, update_ally_status_by_id,
    get_all_orders,
    get_all_pending_support_requests, get_support_request_full,
    get_admin_panel_balances, get_admin_panel_users,
    get_admin_panel_earnings, get_admin_panel_pricing_settings,
    update_admin_panel_pricing_settings, cancel_order_from_admin_panel,
    resolve_support_request_from_admin_panel,
    create_web_user, update_web_user_status,
    get_admin_special_orders_between, get_fee_config,
    get_courier_by_id, get_admin_by_id, get_all_local_admins,
    get_platform_admin,
)


# Router para endpoints administrativos
# Todos los endpoints aquÃ­ tendrÃ¡n el prefijo /admin
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
    require_panel_admin(admin)

    # Obtiene el usuario que se desea aprobar
    user = get_user_by_id(user_id)

    # Si el usuario no existe, retorna error 404
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Ejecuta la acciÃ³n de aprobaciÃ³n (cambia el estado a APPROVED)
    approve_user(user)

    # Retorna el usuario aprobado serializado con UserResponse
    return user


@router.get("/admins", response_model=list[AdminResponse])
def list_admins(admin=Depends(get_current_user)):
    """Lista todos los administradores locales. Solo accesible por el admin de plataforma."""
    require_panel_admin(admin)
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
    require_panel_admin(admin)
    update_admin_status_by_id(admin_id, "APPROVED")
    return {"ok": True}


@router.post("/admins/{admin_id}/reject")
def reject_admin_endpoint(admin_id: int, admin=Depends(require_permission(Permission.REJECT_USER))):
    """Rechaza un administrador local. Solo PLATFORM_ADMIN."""
    update_admin_status_by_id(admin_id, "REJECTED")
    return {"ok": True}


@router.post("/admins/{admin_id}/deactivate")
def deactivate_admin_endpoint(admin_id: int, admin=Depends(get_current_user)):
    """Inactiva un administrador local aprobado."""
    require_panel_admin(admin)
    update_admin_status_by_id(admin_id, "INACTIVE")
    return {"ok": True}


@router.post("/admins/{admin_id}/reactivate")
def reactivate_admin_endpoint(admin_id: int, admin=Depends(get_current_user)):
    """Reactiva un administrador local inactivo."""
    require_panel_admin(admin)
    update_admin_status_by_id(admin_id, "APPROVED")
    return {"ok": True}


@router.get("/couriers", response_model=list[CourierResponse])
def list_couriers(admin=Depends(get_current_user)):
    """Lista todos los repartidores."""
    require_panel_admin(admin)
    rows = get_all_couriers()
    return [{
        "id": r["id"], "full_name": r["full_name"], "phone": r["phone"],
        "city": r["city"], "barrio": r["barrio"], "status": r["status"],
        "id_number": r["id_number"] or "", "plate": r["plate"] or "",
        "bike_type": r["bike_type"] or "",
    } for r in rows]


@router.post("/couriers/{courier_id}/approve")
def approve_courier(courier_id: int, admin=Depends(get_current_user)):
    require_panel_admin(admin)
    update_courier_status_by_id(courier_id, "APPROVED")
    return {"ok": True}


@router.post("/couriers/{courier_id}/reject")
def reject_courier(courier_id: int, admin=Depends(require_permission(Permission.REJECT_USER))):
    """Solo PLATFORM_ADMIN puede rechazar definitivamente."""
    update_courier_status_by_id(courier_id, "REJECTED")
    return {"ok": True}


@router.post("/couriers/{courier_id}/deactivate")
def deactivate_courier(courier_id: int, admin=Depends(get_current_user)):
    require_panel_admin(admin)
    update_courier_status_by_id(courier_id, "INACTIVE")
    return {"ok": True}


@router.post("/couriers/{courier_id}/reactivate")
def reactivate_courier(courier_id: int, admin=Depends(get_current_user)):
    require_panel_admin(admin)
    update_courier_status_by_id(courier_id, "APPROVED")
    return {"ok": True}


@router.get("/allies", response_model=list[AllyResponse])
def list_allies(admin=Depends(get_current_user)):
    """Lista todos los aliados."""
    require_panel_admin(admin)
    rows = get_all_allies()
    return [{
        "id": r["id"], "business_name": r["business_name"], "owner_name": r["owner_name"],
        "phone": r["phone"], "city": r["city"], "barrio": r["barrio"],
        "status": r["status"], "address": r["address"] or "",
    } for r in rows]


@router.post("/allies/{ally_id}/approve")
def approve_ally(ally_id: int, admin=Depends(get_current_user)):
    require_panel_admin(admin)
    update_ally_status_by_id(ally_id, "APPROVED")
    return {"ok": True}


@router.post("/allies/{ally_id}/reject")
def reject_ally(ally_id: int, admin=Depends(require_permission(Permission.REJECT_USER))):
    """Solo PLATFORM_ADMIN puede rechazar definitivamente."""
    update_ally_status_by_id(ally_id, "REJECTED")
    return {"ok": True}


@router.post("/allies/{ally_id}/deactivate")
def deactivate_ally(ally_id: int, admin=Depends(get_current_user)):
    require_panel_admin(admin)
    update_ally_status_by_id(ally_id, "INACTIVE")
    return {"ok": True}


@router.post("/allies/{ally_id}/reactivate")
def reactivate_ally(ally_id: int, admin=Depends(get_current_user)):
    require_panel_admin(admin)
    update_ally_status_by_id(ally_id, "APPROVED")
    return {"ok": True}


@router.get("/couriers/active-locations")
def get_active_courier_locations(admin=Depends(get_current_user)):
    """
    Retorna todos los repartidores con ubicacion en vivo activa (ONLINE).
    Incluye lat/lng, nombre, equipo y timestamp de ultima actualizacion.
    Solo accesible por administradores.
    """
    require_panel_admin(admin)

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
    require_panel_admin(admin)

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
    require_panel_admin(admin)

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
    """Retorna saldos filtrados por equipo (ADMIN_LOCAL) o globales (PLATFORM_ADMIN)."""
    require_panel_admin(admin)
    return get_admin_panel_balances(admin_id=_scoped_admin_id(admin))


@router.get("/users")
def list_all_users(admin=Depends(get_current_user)):
    """Lista usuarios filtrados por equipo (ADMIN_LOCAL) o globales (PLATFORM_ADMIN)."""
    require_panel_admin(admin)
    return get_admin_panel_users(admin_id=_scoped_admin_id(admin))


@router.get("/ganancias")
def get_ganancias(admin=Depends(get_current_user)):
    """Retorna ganancias filtradas por equipo (ADMIN_LOCAL) o globales (PLATFORM_ADMIN)."""
    require_panel_admin(admin)
    return get_admin_panel_earnings(admin_id=_scoped_admin_id(admin))


@router.post("/orders/{order_id}/cancel")
def cancel_order_endpoint(order_id: int, admin=Depends(get_current_user)):
    """Cancela un pedido que aÃºn no ha sido entregado."""
    require_panel_admin(admin)
    try:
        cancel_order_from_admin_panel(order_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"El pedido ya estÃ¡ en estado {str(exc)}")
    return {"ok": True, "order_id": order_id}


@router.get("/settings/pricing")
def get_pricing_settings(admin=Depends(require_permission(Permission.MANAGE_SETTINGS))):
    """Retorna las tarifas de precios. Solo PLATFORM_ADMIN."""
    return get_admin_panel_pricing_settings()


@router.post("/settings/pricing")
def update_pricing_settings(payload: dict, admin=Depends(require_permission(Permission.MANAGE_SETTINGS))):
    """Actualiza las tarifas de precios. Solo PLATFORM_ADMIN."""
    update_admin_panel_pricing_settings(payload)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Solicitudes de ayuda â€” pin mal ubicado
# ---------------------------------------------------------------------------

@router.get("/support-requests")
def list_support_requests(admin=Depends(get_current_user)):
    """Lista todas las solicitudes de ayuda pendientes con datos de courier y pedido."""
    require_panel_admin(admin)
    rows = get_all_pending_support_requests()
    return rows


@router.get("/support-requests/{support_id}")
def get_support_request(support_id: int, admin=Depends(get_current_user)):
    """Retorna detalle completo de una solicitud de ayuda."""
    require_panel_admin(admin)
    req = get_support_request_full(support_id)
    if not req:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    return req


@router.post("/support-requests/{support_id}/resolve")
def resolve_support_request_endpoint(support_id: int, payload: dict, admin=Depends(get_current_user)):
    """
    Resuelve una solicitud de ayuda desde el panel web.
    payload: { "action": "fin" | "cancel_courier" | "cancel_ally", "admin_db_id": int }
    Aplica fees en BD. No envÃ­a notificaciones Telegram (canal bot).
    """
    require_panel_admin(admin)

    action = payload.get("action")
    admin_db_id = payload.get("admin_db_id")
    try:
        order_id = resolve_support_request_from_admin_panel(support_id, action, admin_db_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except LookupError:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    except NotImplementedError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        detail = str(exc)
        if detail == "Solicitud ya resuelta":
            raise HTTPException(status_code=409, detail="Esta solicitud ya fue resuelta")
        raise HTTPException(status_code=409, detail=detail)
    return {"ok": True, "action": action, "order_id": order_id}


# ---------------------------------------------------------------------------
# Usuarios del panel web (solo PLATFORM_ADMIN)
# ---------------------------------------------------------------------------

@router.get("/web-users")
def list_web_users_endpoint(admin=Depends(require_permission(Permission.MANAGE_SETTINGS))):
    """Lista todos los usuarios del panel web."""
    users = list_web_panel_users()
    return [
        {
            "id": u.id,
            "username": u.username,
            "role": u.role.value,
            "status": u.status.value,
            "admin_id": u.admin_id,
        }
        for u in users
    ]


@router.post("/web-users")
def create_web_user_endpoint(
    payload: dict,
    admin=Depends(require_permission(Permission.MANAGE_SETTINGS)),
):
    """Crea un nuevo usuario del panel web. Solo PLATFORM_ADMIN."""
    import bcrypt

    username = (payload.get("username") or "").strip()
    password = (payload.get("password") or "").strip()
    role = payload.get("role", "ADMIN_LOCAL")
    admin_id = payload.get("admin_id")

    if not username or not password:
        raise HTTPException(status_code=400, detail="username y password son requeridos")
    if role not in ("ADMIN_PLATFORM", "ADMIN_LOCAL"):
        raise HTTPException(status_code=400, detail="role invalido")

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        new_id = create_web_user(username, hashed, role=role, admin_id=admin_id or None)
    except Exception as exc:
        msg = str(exc)
        if "UNIQUE" in msg or "unique" in msg.lower() or "duplicate" in msg.lower():
            raise HTTPException(status_code=409, detail="El nombre de usuario ya existe")
        raise HTTPException(status_code=500, detail="Error al crear el usuario")
    return {"ok": True, "id": new_id}


@router.get("/pedidos-especiales/metricas")
def get_pedidos_especiales_metricas(
    periodo: str = "semana",
    admin_filter: int = None,
    current_user=Depends(get_current_user),
):
    """Metricas de rentabilidad de pedidos especiales del admin.

    periodo: hoy | ayer | semana | mes | todo
    admin_filter: solo ADMIN_PLATFORM puede filtrar por admin_id (None = todos)
    ADMIN_LOCAL solo ve sus propios pedidos.
    """
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if periodo == "hoy":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif periodo == "ayer":
        yesterday = now - timedelta(days=1)
        start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif periodo == "semana":
        start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif periodo == "mes":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now
    else:  # todo
        start = datetime(2024, 1, 1)
        end = now

    start_s = start.strftime("%Y-%m-%d %H:%M:%S")
    end_s = end.strftime("%Y-%m-%d %H:%M:%S")

    fee_cfg = get_fee_config()
    platform_share = fee_cfg.get("fee_platform_share", 100)
    tech_dev_pct = fee_cfg.get("fee_special_order_tech_dev_pct", 2)

    # Determinar qué admins mostrar
    scoped_admin_id = _scoped_admin_id(current_user)
    if scoped_admin_id is not None:
        admin_ids = [scoped_admin_id]
    elif admin_filter:
        admin_ids = [admin_filter]
    else:
        # PLATFORM_ADMIN sin filtro: todos los admins locales + plataforma
        all_admins = get_all_local_admins()
        admin_ids = [a["id"] for a in all_admins]
        platform_admin = get_platform_admin()
        if platform_admin:
            pa_id = platform_admin["id"] if isinstance(platform_admin, dict) else platform_admin[0]
            if pa_id not in admin_ids:
                admin_ids.append(pa_id)

    orders_all = []
    seen_order_ids = set()
    for aid in admin_ids:
        rows = get_admin_special_orders_between(aid, start_s, end_s)
        for r in rows:
            row = dict(r) if not isinstance(r, dict) else r
            oid = row.get("id")
            if oid in seen_order_ids:
                continue
            seen_order_ids.add(oid)
            row["_creator_admin_id"] = aid
            orders_all.append(row)

    # Batch-lookup de nombres de courier (1 query por courier único, no por pedido)
    unique_courier_ids = {int(o["courier_id"]) for o in orders_all if o.get("courier_id")}
    courier_names = {}
    for cid in unique_courier_ids:
        try:
            c = get_courier_by_id(cid)
            if c:
                courier_names[cid] = c["full_name"] if isinstance(c, dict) else c[0]
        except Exception:
            pass

    # Calcular métricas por pedido
    result_orders = []
    total_tarifas = 0
    total_comisiones = 0
    total_fees_admin = 0
    total_ganancia_neta = 0
    total_delivered = 0
    total_cancelled = 0

    for order in orders_all:
        total_fee = int(order.get("total_fee") or 0)
        special_commission = int(order.get("special_commission") or 0)
        status = order.get("status", "")

        # Calcular fees del admin creador (solo aplica en DELIVERED)
        if status == "DELIVERED":
            platform_fee = platform_share
            tech_dev_fee = round(total_fee * tech_dev_pct / 100) if special_commission > 0 else 0
            fee_admin_pagado = platform_fee + tech_dev_fee
            ganancia_neta = special_commission - fee_admin_pagado
        else:
            platform_fee = 0
            tech_dev_fee = 0
            fee_admin_pagado = 0
            ganancia_neta = 0

        # Nombre del courier desde el dict pre-cargado
        courier_id = order.get("courier_id")
        courier_name = courier_names.get(int(courier_id)) if courier_id else None

        if status == "DELIVERED":
            total_tarifas += total_fee
            total_comisiones += special_commission
            total_fees_admin += fee_admin_pagado
            total_ganancia_neta += ganancia_neta
            total_delivered += 1
        else:
            total_cancelled += 1

        result_orders.append({
            "id": order.get("id"),
            "created_at": str(order.get("created_at") or ""),
            "status": status,
            "total_fee": total_fee,
            "special_commission": special_commission,
            "platform_fee": platform_fee,
            "tech_dev_fee": tech_dev_fee,
            "fee_admin_pagado": fee_admin_pagado,
            "ganancia_neta": ganancia_neta,
            "courier_name": courier_name,
            "customer_name": order.get("customer_name"),
            "customer_barrio": order.get("customer_barrio"),
            "customer_city": order.get("customer_city"),
            "creator_admin_id": order.get("creator_admin_id"),
        })

    return {
        "periodo": periodo,
        "resumen": {
            "total_pedidos": len(result_orders),
            "entregados": total_delivered,
            "cancelados": total_cancelled,
            "total_tarifas": total_tarifas,
            "total_comisiones": total_comisiones,
            "total_fees_admin": total_fees_admin,
            "ganancia_neta": total_ganancia_neta,
        },
        "pedidos": result_orders,
    }


@router.patch("/web-users/{user_id}/status")
def update_web_user_status_endpoint(
    user_id: int,
    payload: dict,
    admin=Depends(require_permission(Permission.MANAGE_SETTINGS)),
):
    """Activa o inactiva un usuario del panel web. Solo PLATFORM_ADMIN."""
    status = payload.get("status")
    if status not in ("APPROVED", "INACTIVE"):
        raise HTTPException(status_code=400, detail="status debe ser APPROVED o INACTIVE")
    update_web_user_status(user_id, status)
    return {"ok": True}
