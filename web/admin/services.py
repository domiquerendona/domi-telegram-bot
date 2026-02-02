# Importa el enum que define los posibles estados del usuario
# Ejemplo: PENDING, APPROVED, REJECTED, INACTIVE
from web.users.models import UserStatus


def approve_user(user):
    """
    Aprueba un usuario pendiente.

    Cambia el estado del usuario a APPROVED,
    indicando que puede acceder al sistema.
    """
    user.status = UserStatus.APPROVED
    return user


def reject_user(user):
    """
    Rechaza un usuario.

    Cambia el estado del usuario a REJECTED,
    indicando que su solicitud fue negada.
    """
    user.status = UserStatus.REJECTED
    return user


def deactivate_user(user):
    """
    Desactiva un usuario.

    Cambia el estado del usuario a INACTIVE,
    impidiendo su acceso al sistema sin eliminarlo.
    """
    user.status = UserStatus.INACTIVE
    return user
