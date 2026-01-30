from .models import UserRole

"""
Reglas de acceso basadas en roles (RBAC).

Este archivo centraliza los permisos del sistema y define
qué roles pueden acceder a determinadas áreas o ejecutar
acciones específicas.

Beneficios:
- Evita permisos duplicados en el código
- Facilita cambios futuros en reglas de acceso
- Mejora la seguridad y mantenibilidad del sistema
"""


# Acceso exclusivo del administrador global

PLATFORM_ADMIN_ONLY = {
    UserRole.PLATFORM_ADMIN  # Control total de la plataforma
}

# Acceso permitido a administradores
# (global y local)
ADMIN_ALLOWED = {
    UserRole.PLATFORM_ADMIN,  # Administrador global
    UserRole.ADMIN_LOCAL      # Administrador de sede / negocio
}

# Acceso exclusivo para repartidores
COURIER_ONLY = {
    UserRole.COURIER  # Usuario encargado de realizar domicilios
}

# Acceso exclusivo para aliados (negocios)
ALLY_ONLY = {
    UserRole.ALLY  # Negocios o socios comerciales
}

# Roles autorizados para operar pedidos
# (crear, asignar, actualizar estados, etc.)
CAN_OPERATE_ORDERS = {
    UserRole.COURIER,          # Ejecuta entregas
    UserRole.ADMIN_LOCAL,      # Gestiona pedidos locales
    UserRole.PLATFORM_ADMIN    # Control total
}
