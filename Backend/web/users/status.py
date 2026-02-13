from .models import UserStatus

"""
Reglas de operación basadas en el estado del usuario.

Este archivo define qué acciones puede realizar un usuario
según su estado actual dentro del sistema.

Objetivo:
- Centralizar la lógica de acceso por estado
- Evitar validaciones repetidas en el código
- Facilitar el control del ciclo de vida del usuario
"""

# Usuarios activos y aprobados
# Pueden usar el sistema normalmente

ACTIVE_USERS = {
    UserStatus.APPROVED  # Usuario validado y habilitado
}

# Usuarios bloqueados
# No pueden acceder ni operar en el sistema

BLOCKED_USERS = {
    UserStatus.REJECTED,  # Usuario rechazado por validación
    UserStatus.INACTIVE   # Usuario desactivado (temporal o permanente)
}

# Usuarios pendientes de aprobación
# Acceso restringido o limitado

PENDING_USERS = {
    UserStatus.PENDING  # Usuario en espera de aprobación
}
