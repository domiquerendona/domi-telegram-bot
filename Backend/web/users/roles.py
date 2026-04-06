from enum import Enum
from .models import UserRole


# ---------------------------------------------------------------------------
# Permisos individuales por acción
# ---------------------------------------------------------------------------

class Permission(str, Enum):
    """
    Acciones específicas que un rol puede ejecutar en el panel web.

    Cada endpoint debe declarar qué Permission requiere.
    El mapping ROLE_PERMISSIONS define qué roles tienen qué permisos.
    """

    VIEW_DASHBOARD          = "view_dashboard"
    VIEW_USERS              = "view_users"
    APPROVE_USER            = "approve_user"
    REJECT_USER             = "reject_user"           # Solo PLATFORM_ADMIN
    DEACTIVATE_USER         = "deactivate_user"
    REACTIVATE_USER         = "reactivate_user"
    VIEW_COURIERS_MAP       = "view_couriers_map"
    VIEW_UNASSIGNED_ORDERS  = "view_unassigned_orders"
    MANAGE_SETTINGS         = "manage_settings"       # Solo PLATFORM_ADMIN
    VIEW_OWN_EARNINGS       = "view_own_earnings"     # Courier: sus propias ganancias
    VIEW_OWN_PROFILE        = "view_own_profile"      # Todos: ver perfil propio


# ---------------------------------------------------------------------------
# Mapping rol → conjunto de permisos
# ---------------------------------------------------------------------------

ROLE_PERMISSIONS: dict[UserRole, set[Permission]] = {
    UserRole.PLATFORM_ADMIN: {
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_USERS,
        Permission.APPROVE_USER,
        Permission.REJECT_USER,        # Exclusivo: estado terminal REJECTED
        Permission.DEACTIVATE_USER,
        Permission.REACTIVATE_USER,
        Permission.VIEW_COURIERS_MAP,
        Permission.VIEW_UNASSIGNED_ORDERS,
        Permission.MANAGE_SETTINGS,    # Exclusivo: configuración global
        Permission.VIEW_OWN_PROFILE,
    },
    UserRole.ADMIN_LOCAL: {
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_USERS,
        Permission.APPROVE_USER,
        # SIN REJECT_USER: Admin Local no puede rechazar definitivamente
        Permission.DEACTIVATE_USER,
        Permission.REACTIVATE_USER,
        Permission.VIEW_COURIERS_MAP,
        Permission.VIEW_UNASSIGNED_ORDERS,
        # SIN MANAGE_SETTINGS: configuración es exclusiva de plataforma
        Permission.VIEW_OWN_PROFILE,
    },
    UserRole.COURIER: {
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_OWN_EARNINGS,
        Permission.VIEW_OWN_PROFILE,
    },
    UserRole.ALLY: set(),   # Sin acceso al panel web
}


# ---------------------------------------------------------------------------
# Grupos de roles (compatibilidad con código existente)
# ---------------------------------------------------------------------------

PLATFORM_ADMIN_ONLY = {UserRole.PLATFORM_ADMIN}

ADMIN_ALLOWED = {
    UserRole.PLATFORM_ADMIN,
    UserRole.ADMIN_LOCAL,
}

COURIER_ONLY = {UserRole.COURIER}

ALLY_ONLY = {UserRole.ALLY}

CAN_OPERATE_ORDERS = {
    UserRole.COURIER,
    UserRole.ADMIN_LOCAL,
    UserRole.PLATFORM_ADMIN,
}
