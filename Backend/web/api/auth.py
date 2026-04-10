"""
Endpoints de autenticación para el panel web administrativo.
- POST /auth/login: login con usuario/contraseña
- POST /auth/forgot-password: reset via Telegram
"""
import os
import random
import string
import logging

import bcrypt
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from web.auth.token import create_token
from web.users.repository import get_web_user_by_username
from web.users.status import ACTIVE_USERS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])

_GENERIC_RESET_MSG = "Si el usuario existe, recibirás una contraseña temporal en Telegram."


class LoginRequest(BaseModel):
    username: str
    password: str


class ForgotPasswordRequest(BaseModel):
    username: str


def _random_password(length: int = 10) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=length))


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


@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordRequest):
    """
    Genera una contraseña temporal y la envía al Telegram del usuario.
    Siempre retorna el mismo mensaje para evitar enumeración de usuarios.
    Requiere la variable TELEGRAM_BOT_TOKEN en el servicio API de Railway.
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not bot_token:
        logger.warning("forgot-password: TELEGRAM_BOT_TOKEN no configurado")
        raise HTTPException(
            status_code=503,
            detail="El reset de contraseña no está disponible en este momento.",
        )

    username = body.username.strip()

    from db import get_web_user_by_username as _db_get, get_telegram_id_for_web_user, update_web_user_password
    row = _db_get(username)
    if row is None:
        # Respuesta genérica — no revelar si el usuario existe
        return {"message": _GENERIC_RESET_MSG}

    user_id = row["id"] if isinstance(row, dict) else row[0]
    status = row["status"] if isinstance(row, dict) else row[4]
    if status not in ACTIVE_USERS:
        return {"message": _GENERIC_RESET_MSG}

    telegram_id = get_telegram_id_for_web_user(username)
    if not telegram_id:
        logger.warning("forgot-password: no se encontró telegram_id para '%s'", username)
        return {"message": _GENERIC_RESET_MSG}

    temp_password = _random_password(10)
    hashed = bcrypt.hashpw(temp_password.encode(), bcrypt.gensalt()).decode()
    update_web_user_password(user_id, hashed)

    msg = (
        "Solicitaste restablecer tu contrasena del panel web.\n\n"
        "Tu contrasena temporal es:\n"
        "{}\n\n"
        "Ingresa con ella y cambiala desde Mi perfil."
    ).format(temp_password)

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": telegram_id, "text": msg},
            timeout=10,
        )
        if not resp.ok:
            logger.error("forgot-password: Telegram API error %s: %s", resp.status_code, resp.text)
    except Exception as e:
        logger.error("forgot-password: error enviando mensaje Telegram: %s", e)

    return {"message": _GENERIC_RESET_MSG}
