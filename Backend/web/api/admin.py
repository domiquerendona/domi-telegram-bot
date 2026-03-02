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

# Schema de respuesta para serializar el usuario aprobado
from web.schemas.user import UserResponse

# Funciones de acceso a datos para ubicaciones en tiempo real
from db import get_all_online_couriers, get_active_orders_without_courier


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
