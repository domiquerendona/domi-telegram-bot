from fastapi import APIRouter, Depends

from web.auth.dependencies import get_current_user
from web.auth.guards import require_panel_admin
from services import get_dashboard_stats


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats")
def dashboard_stats(current_user=Depends(get_current_user)):
    """
    Estadísticas reales del panel: usuarios, pedidos, saldo y ganancias.
    """
    require_panel_admin(current_user)
    return get_dashboard_stats()
