from fastapi import HTTPException

from web.users.models import UserRole, UserStatus
from web.users.roles import ADMIN_ALLOWED, Permission, ROLE_PERMISSIONS
from web.users.status import ACTIVE_USERS, BLOCKED_USERS


def can_access_system(user) -> bool:
    """Verifica si el estado del usuario le permite operar en el panel."""
    return user.status in ACTIVE_USERS


def is_admin(user) -> bool:
    """Verifica si el usuario tiene rol administrativo (plataforma o local)."""
    return user.role in ADMIN_ALLOWED


def is_blocked(user) -> bool:
    """Verifica si el usuario está bloqueado."""
    return user.status in BLOCKED_USERS


def has_permission(user, permission: Permission) -> bool:
    """
    Verifica si el rol del usuario tiene un permiso específico.

    Consulta el mapping ROLE_PERMISSIONS en roles.py.
    Retorna False si el rol no está en el mapping.
    """
    allowed = ROLE_PERMISSIONS.get(user.role, set())
    return permission in allowed


# ---------------------------------------------------------------------------
# Guards que lanzan HTTPException (para uso directo en handlers)
# ---------------------------------------------------------------------------

def require_panel_access(user):
    """Exige que el usuario esté habilitado para usar el panel."""
    if not can_access_system(user):
        raise HTTPException(status_code=403, detail="Usuario bloqueado")
    return user


def require_panel_admin(user):
    """Exige acceso al panel y rol administrativo (plataforma o local)."""
    require_panel_access(user)
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="No autorizado")
    return user


def require_permission_guard(user, permission: Permission):
    """
    Exige que el usuario tenga un permiso específico.
    Lanza 403 si no tiene el permiso.
    """
    require_panel_access(user)
    if not has_permission(user, permission):
        raise HTTPException(
            status_code=403,
            detail=f"No autorizado para esta accion"
        )
    return user
