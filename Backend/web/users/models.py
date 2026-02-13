from enum import Enum

class UserRole(str, Enum):
    """
    Enumeración de roles de usuario dentro del sistema.

    Se usa para:
    - Evitar strings mágicos ("ADMIN", "admin", etc.)
    - Garantizar que un usuario solo tenga un rol válido
    - Facilitar validaciones, permisos y control de acceso

    Hereda de:
    - str  → permite tratar los valores como strings (BD, JSON, APIs)
    - Enum → restringe los valores a los definidos aquí
    """

    PLATFORM_ADMIN = "ADMIN_PLATFORM"  # Administrador global de la plataforma
    ADMIN_LOCAL = "ADMIN_LOCAL"        # Administrador de una sede/negocio específico
    COURIER = "COURIER"                # Repartidor / mensajero
    ALLY = "ALLY"                      # Aliado (negocio, socio, tienda, etc.)


class UserStatus(str, Enum):
    """
    Enumeración de estados posibles de un usuario.

    Se usa para:
    - Controlar el ciclo de vida del usuario
    - Validar si puede acceder al sistema
    - Manejar procesos de aprobación y desactivación
    """

    PENDING = "PENDING"     # Usuario creado pero aún no aprobado
    APPROVED = "APPROVED"   # Usuario aprobado y activo
    REJECTED = "REJECTED"   # Usuario rechazado (no puede usar el sistema)
    INACTIVE = "INACTIVE"   # Usuario desactivado temporal o permanentemente
