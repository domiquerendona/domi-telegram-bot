# Importa los enums que definen los roles y estados posibles de un usuario
# Usar enums evita errores por strings mal escritos y centraliza reglas
from web.users.models import UserRole, UserStatus

# Importa el conjunto de roles que tienen permisos administrativos
# Ejemplo: {ADMIN, SUPERADMIN}
from web.users.roles import ADMIN_ALLOWED

# Importa los conjuntos de estados permitidos y bloqueados
# ACTIVE_USERS: usuarios que pueden usar el sistema
# BLOCKED_USERS: usuarios que NO pueden acceder
from web.users.status import ACTIVE_USERS, BLOCKED_USERS


def can_access_system(user) -> bool:
    """
    Verifica si el usuario puede usar el sistema.

    Retorna True si el estado del usuario se encuentra
    dentro de los estados permitidos (ACTIVE_USERS).
    """
    return user.status in ACTIVE_USERS


def is_admin(user) -> bool:
    """
    Verifica si el usuario tiene permisos administrativos.

    Retorna True si el rol del usuario pertenece
    al conjunto de roles administradores.
    """
    return user.role in ADMIN_ALLOWED


def is_blocked(user) -> bool:
    """
    Verifica si el usuario está bloqueado.

    Retorna True si el estado del usuario está
    dentro de los estados bloqueados.
    """
    return user.status in BLOCKED_USERS
