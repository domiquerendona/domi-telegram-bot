# Importa utilidades de FastAPI para definir rutas, dependencias y errores HTTP
from fastapi import APIRouter, Depends, HTTPException

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
