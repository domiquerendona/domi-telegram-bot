# Router y dependencias de FastAPI
from fastapi import APIRouter, Depends

# Dependencia que obtiene el usuario autenticado
from web.auth.dependencies import get_current_user

# Guard que valida permisos administrativos
from web.auth.guards import is_admin

# Función del repository que devuelve la lista de usuarios
from web.users.repository import list_users

# Enum de estados de usuario
from web.users.models import UserStatus


# Router para endpoints del dashboard administrativo
# Prefijo /dashboard
router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats")
def dashboard_stats(current_user=Depends(get_current_user)):
    """
    Estadísticas básicas para el panel administrativo.
    """

    # Verifica que el usuario autenticado sea administrador
    if not is_admin(current_user):
        return {"detail": "No autorizado"}

    # Obtiene todos los usuarios (mock o BD)
    users = list_users()

    # Retorna métricas calculadas a partir del estado de los usuarios
    return {
        # Total de usuarios registrados
        "total_users": len(users),

        # Usuarios pendientes de aprobación
        "pending_users": len([
            u for u in users if u.status == UserStatus.PENDING
        ]),

        # Usuarios activos y aprobados
        "active_users": len([
            u for u in users if u.status == UserStatus.APPROVED
        ]),

        # Usuarios bloqueados (rechazados o inactivos)
        "blocked_users": len([
            u for u in users if u.status in {
                UserStatus.REJECTED,
                UserStatus.INACTIVE
            }
        ])
    }
