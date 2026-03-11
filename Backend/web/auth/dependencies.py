from fastapi import Header, HTTPException
from web.auth.token import verify_token


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
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

    class AuthUser:
        role = "ADMIN_PLATFORM"
        status = "APPROVED"

    return AuthUser()
