from fastapi import Header, HTTPException

from web.auth.token import verify_token
from web.users.repository import get_configured_web_user


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
