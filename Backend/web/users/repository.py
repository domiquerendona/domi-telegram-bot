# Importa los enums que definen roles y estados válidos del usuario
# Esto evita usar strings sueltos y asegura consistencia en todo el sistema
from web.users.models import UserRole, UserStatus


class User:
    """
    Entidad Usuario simulada (mock).

    Representa la estructura básica de un usuario
    mientras no existe aún la base de datos real.
    """

    def __init__(self, id: int, role: UserRole, status: UserStatus):
        # Identificador único del usuario
        self.id = id

        # Rol del usuario dentro del sistema (admin, courier, etc.)
        self.role = role

        # Estado actual del usuario (aprobado, pendiente, inactivo, etc.)
        self.status = status


# ------------------ Base de datos simulada ------------------

# Lista en memoria que simula una tabla de usuarios
# Se usa solo para desarrollo y pruebas
_USERS = [
    User(1, UserRole.PLATFORM_ADMIN, UserStatus.APPROVED),
    User(2, UserRole.ADMIN_LOCAL, UserStatus.APPROVED),
    User(3, UserRole.COURIER, UserStatus.PENDING),
    User(4, UserRole.ALLY, UserStatus.INACTIVE),
]


def list_users():
    """
    Devuelve todos los usuarios del sistema.

    Usado por:
    - Panel administrativo
    - Dashboard
    - Listados en la web

    Retorna una lista de objetos User.
    """
    return _USERS


def get_user_by_id(user_id: int):
    """
    Busca un usuario por su ID.

    Recorre la lista de usuarios simulada y retorna:
    - El usuario si existe
    - None si no se encuentra
    """
    return next((user for user in _USERS if user.id == user_id), None)
