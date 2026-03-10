"""
Endpoint de login para el panel web administrativo.
Valida usuario/contraseña contra variables de entorno y retorna un token HMAC.
"""
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from web.auth.token import create_token

router = APIRouter(prefix="/auth", tags=["Auth"])

_WEB_USER = os.getenv("WEB_ADMIN_USER", "admin")
_WEB_PASS = os.getenv("WEB_ADMIN_PASSWORD", "changeme")


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(body: LoginRequest):
    """
    Autentica al administrador del panel web.
    Credenciales configuradas en WEB_ADMIN_USER y WEB_ADMIN_PASSWORD.
    """
    if body.username != _WEB_USER or body.password != _WEB_PASS:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    token = create_token(body.username)
    return {"token": token, "username": body.username}
