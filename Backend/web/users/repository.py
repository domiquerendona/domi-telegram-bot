import os
from dataclasses import dataclass

from web.users.models import UserRole, UserStatus


@dataclass
class WebUser:
    """
    Identidad minima real del panel web.

    En esta fase el sistema expone un unico usuario web configurable por entorno.
    No reemplaza un sistema multiusuario completo.
    """

    id: int
    username: str
    role: UserRole
    status: UserStatus


def get_configured_web_user() -> WebUser:
    username = os.getenv("WEB_ADMIN_USER", "admin").strip()
    user_id = int(os.getenv("WEB_ADMIN_ID", "1"))
    role = UserRole(os.getenv("WEB_ADMIN_ROLE", UserRole.PLATFORM_ADMIN.value).strip().upper())
    status = UserStatus(os.getenv("WEB_ADMIN_STATUS", UserStatus.APPROVED.value).strip().upper())
    return WebUser(
        id=user_id,
        username=username,
        role=role,
        status=status,
    )


def list_users():
    """
    Devuelve la identidad real minima del panel web.

    Esta fase no implementa catalogo completo de usuarios web.
    """
    return [get_configured_web_user()]


def get_user_by_id(user_id: int):
    """
    Busca el unico usuario web real configurado por entorno.
    """
    user = get_configured_web_user()
    return user if user.id == user_id else None
