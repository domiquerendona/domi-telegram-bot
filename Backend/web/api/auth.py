"""
Endpoint de login para el panel web administrativo.
Valida usuario/contraseña contra la tabla web_users con bcrypt.
"""
import bcrypt
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from web.auth.token import create_token
from web.users.repository import get_web_user_by_username
from web.users.status import ACTIVE_USERS

router = APIRouter(prefix="/auth", tags=["Auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(body: LoginRequest):
    """
    Autentica un usuario del panel web.
    Verifica contraseña con bcrypt contra web_users en BD.
    """
    user = get_web_user_by_username(body.username.strip())
    if not user:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    if user.status not in ACTIVE_USERS:
        raise HTTPException(status_code=403, detail="Usuario inactivo o bloqueado")

    from db import get_web_user_by_username as _db_get
    row = _db_get(body.username.strip())
    if row is None:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    stored_hash = row["password_hash"] if isinstance(row, dict) else row[2]
    if not bcrypt.checkpw(body.password.encode(), stored_hash.encode()):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    token = create_token(body.username.strip())
    return {"token": token, "username": body.username.strip(), "role": user.role.value}
