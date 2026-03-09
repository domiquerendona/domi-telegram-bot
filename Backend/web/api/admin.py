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
    get_all_orders,
)


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
