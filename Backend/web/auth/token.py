"""
Utilidad de tokens HMAC para autenticación del panel web.
No requiere dependencias externas — usa solo stdlib de Python.

Token format: base64url(payload) + "." + hmac_sha256(secret, base64url(payload))
Payload: "username|expiry_unix_timestamp"
"""
import hmac
import hashlib
import base64
import time
import os
from typing import Optional

_TOKEN_TTL = 60 * 60 * 24  # 24 horas


def _secret() -> str:
    return os.getenv("WEB_SECRET_KEY", "domi-dev-secret-change-in-prod")


def _b64(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")


def _sign(payload_b64: str) -> str:
    return hmac.new(_secret().encode(), payload_b64.encode(), hashlib.sha256).hexdigest()


def create_token(username: str) -> str:
    expiry = int(time.time()) + _TOKEN_TTL
    payload_b64 = _b64(f"{username}|{expiry}")
    sig = _sign(payload_b64)
    return f"{payload_b64}.{sig}"


def verify_token(token: str) -> Optional[str]:
    """Verifica el token. Retorna el username si es válido, None si no."""
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, sig = parts

        # Verificar firma (comparación segura contra timing attacks)
        expected_sig = _sign(payload_b64)
        if not hmac.compare_digest(sig, expected_sig):
            return None

        # Decodificar payload
        padding = 4 - len(payload_b64) % 4
        payload = base64.urlsafe_b64decode(payload_b64 + "=" * padding).decode()
        username, expiry_str = payload.split("|", 1)

        # Verificar expiración
        if int(time.time()) > int(expiry_str):
            return None

        return username
    except Exception:
        return None
