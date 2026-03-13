from fastapi import Header, HTTPException, Depends

from web.auth.token import verify_token
from web.users.repository import get_configured_web_user
from web.users.roles import Permission
from web.auth.guards import require_panel_access, has_permission


def _resolve_web_admin_user(username: str):
    user = get_configured_web_user()
    if username != user.username:
        raise HTTPException(status_code=401, detail="Usuario autenticado no reconocido")
    return user


def get_current_user(authorization: str = Header(default="")):
    """
    Dependencia FastAPI que valida el token del header Authorization.
    Formato esperado: "Bearer <token>"
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token requerido")

    token = authorization.removeprefix("Bearer ").strip()
    username = verify_token(token)

    if not username:
        raise HTTPException(status_code=401, detail="Token invalido o expirado")

    return _resolve_web_admin_user(username)


def require_permission(permission: Permission):
    """
    Factory de dependencias FastAPI para RBAC fino.

    Uso en endpoints:
        @router.post("/admins/{id}/reject")
        def reject_admin(admin_id: int, admin=Depends(require_permission(Permission.REJECT_USER))):
            ...

    Verifica autenticación, estado activo y permiso específico del rol.
    Lanza 403 si el rol no tiene el permiso requerido.
    """
    def dependency(current_user=Depends(get_current_user)):
        require_panel_access(current_user)
        if not has_permission(current_user, permission):
            raise HTTPException(status_code=403, detail="No autorizado para esta accion")
        return current_user
    return dependency
