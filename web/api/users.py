# Router de FastAPI para agrupar endpoints relacionados con usuarios
from fastapi import APIRouter, Depends, HTTPException

# Dependencia que devuelve el usuario autenticado
from web.auth.dependencies import get_current_user

# Guard que valida si el usuario puede acceder al sistema
from web.auth.guards import can_access_system

# Funciones de acceso a datos (repository)
from web.users.repository import get_user_by_id, list_users


# Se define el router con prefijo /users
# Todos los endpoints aquí comenzarán con /users
router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/")
def get_users(current_user=Depends(get_current_user)):
    """
    Lista todos los usuarios.
    Usado por paneles administrativos o listados web.
    """

    # Verifica si el usuario autenticado tiene acceso al sistema
    if not can_access_system(current_user):
        raise HTTPException(status_code=403, detail="Usuario bloqueado")

    # Retorna la lista de usuarios desde el repository
    return list_users()


@router.get("/me")
def get_my_profile(current_user=Depends(get_current_user)):
    """
    Devuelve el perfil del usuario autenticado.
    Usado por la página 'Mi cuenta'.
    """

    # Retorna directamente el usuario autenticado
    return current_user


@router.get("/{user_id}")
def get_user_detail(
    user_id: int,
    current_user=Depends(get_current_user)
):
    """
    Devuelve información de un usuario por ID.
    """

    # Verifica que el usuario tenga permiso para acceder al sistema
    if not can_access_system(current_user):
        raise HTTPException(status_code=403, detail="Usuario bloqueado")

    # Obtiene el usuario solicitado
    user = get_user_by_id(user_id)

    # Si el usuario no existe, retorna error 404
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Retorna la información del usuario
    return user
