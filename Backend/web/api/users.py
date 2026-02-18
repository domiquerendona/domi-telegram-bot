# Importa utilidades de FastAPI para crear rutas, dependencias y manejar errores HTTP
from fastapi import APIRouter, Depends, HTTPException

# Dependencia que obtiene el usuario autenticado (mock o JWT en el futuro)
from web.auth.dependencies import get_current_user

# Guard que valida si el usuario puede acceder al sistema según su estado
from web.auth.guards import can_access_system

# Funciones del repository para obtener usuarios
from web.users.repository import get_user_by_id, list_users

# Schema de salida que define cómo se envían los usuarios al frontend
from web.schemas.user import UserResponse


# Se define el router para todos los endpoints de usuarios
# Todos los endpoints aquí tendrán el prefijo /users
router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=list[UserResponse])
def get_users(current_user=Depends(get_current_user)):
    """
    Lista todos los usuarios.
    Usado por paneles administrativos o listados web.
    """

    # Verifica si el usuario autenticado tiene permiso para usar el sistema
    if not can_access_system(current_user):
        raise HTTPException(status_code=403, detail="Usuario bloqueado")

    # Retorna la lista de usuarios usando el schema UserResponse
    return list_users()


@router.get("/me", response_model=UserResponse)
def get_my_profile(current_user=Depends(get_current_user)):
    """
    Devuelve el perfil del usuario autenticado.
    Usado por la página 'Mi cuenta'.
    """

    # Retorna el usuario autenticado serializado con UserResponse
    return current_user


@router.get("/{user_id}", response_model=UserResponse)
def get_user_detail(
    user_id: int,
    current_user=Depends(get_current_user)
):
    """
    Devuelve información de un usuario por ID.
    """

    # Verifica si el usuario autenticado puede acceder al sistema
    if not can_access_system(current_user):
        raise HTTPException(status_code=403, detail="Usuario bloqueado")

    # Obtiene el usuario solicitado desde el repository
    user = get_user_by_id(user_id)

    # Si el usuario no existe, retorna error 404
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Retorna el usuario encontrado serializado con UserResponse
    return user
