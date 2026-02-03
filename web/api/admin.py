# Router de FastAPI para definir endpoints
from fastapi import APIRouter, Depends, HTTPException

# Guard que valida si un usuario tiene permisos de administrador
from web.auth.guards import is_admin

# Servicios administrativos que contienen la lógica de negocio
from web.admin.services import approve_user, reject_user, deactivate_user

# Repositorio que obtiene usuarios por ID (mock o BD)
from web.users.repository import get_user_by_id

# Dependencia que obtiene el usuario autenticado actual
from web.auth.dependencies import get_current_user


# Se crea un router con prefijo /admin
# Todos los endpoints aquí definidos serán administrativos
router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/users/{user_id}/approve")
def approve_user_endpoint(
    user_id: int,
    admin=Depends(get_current_user)
):
    """
    Endpoint para aprobar un usuario por su ID.

    Solo accesible por usuarios con rol administrador.
    """

    # Verifica si el usuario autenticado tiene permisos administrativos
    if not is_admin(admin):
        # Si no es admin, se bloquea el acceso
        raise HTTPException(status_code=403, detail="No autorizado")

    # Obtiene el usuario a aprobar desde el repositorio
    user = get_user_by_id(user_id)

    # Ejecuta la lógica de negocio para aprobar al usuario
    approve_user(user)

    # Retorna una respuesta clara al cliente
    return {
        "message": "Usuario aprobado",
        "status": user.status
    }
