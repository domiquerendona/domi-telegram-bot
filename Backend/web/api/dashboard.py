from fastapi import APIRouter, Depends

from web.auth.dependencies import get_current_user
from web.auth.guards import require_panel_admin
from web.users.models import UserRole
from services import get_dashboard_stats


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats")
def dashboard_stats(current_user=Depends(get_current_user)):
    """
    Estadísticas del panel filtradas por equipo (ADMIN_LOCAL) o globales (PLATFORM_ADMIN).
    """
    require_panel_admin(current_user)
    admin_id = current_user.admin_id if current_user.role == UserRole.ADMIN_LOCAL else None
    return get_dashboard_stats(admin_id=admin_id)
