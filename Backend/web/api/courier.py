"""
Endpoints del panel web para repartidores (COURIER).
Solo lectura — no modifica nada del bot.
"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException

from web.auth.dependencies import get_current_user
from web.users.models import UserRole
from db import get_courier_web_dashboard, get_courier_web_earnings, get_courier_web_profile

router = APIRouter(prefix="/courier", tags=["Courier"])


def _require_courier(current_user=Depends(get_current_user)):
    """Exige que el usuario sea COURIER y tenga courier_id vinculado."""
    if current_user.role != UserRole.COURIER:
        raise HTTPException(status_code=403, detail="Solo accesible para repartidores")
    if not current_user.courier_id:
        raise HTTPException(status_code=403, detail="Cuenta no vinculada a un repartidor")
    return current_user


@router.get("/dashboard")
def courier_dashboard(user=Depends(_require_courier)):
    """Dashboard del repartidor: entregas hoy/mes, tarifa mes, saldo."""
    return get_courier_web_dashboard(user.courier_id)


@router.get("/earnings")
def courier_earnings(period: str = "mes", user=Depends(_require_courier)):
    """
    Ganancias del repartidor filtradas por periodo.
    period: hoy | semana | mes
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if period == "hoy":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "semana":
        start = now - timedelta(days=now.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    else:  # mes
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    start_s = start.strftime("%Y-%m-%d %H:%M:%S")
    end_s = now.strftime("%Y-%m-%d %H:%M:%S")
    orders = get_courier_web_earnings(user.courier_id, start_s, end_s)

    total_tarifa = sum(o["total_fee"] for o in orders)
    total_incentivo = sum(o["incentivo"] for o in orders)

    return {
        "period": period,
        "orders": orders,
        "total_tarifa": total_tarifa,
        "total_incentivo": total_incentivo,
        "total": total_tarifa + total_incentivo,
        "count": len(orders),
    }


@router.get("/profile")
def courier_profile(user=Depends(_require_courier)):
    """Perfil del repartidor."""
    profile = get_courier_web_profile(user.courier_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")
    return {**profile, "username": user.username, "role": user.role.value}
