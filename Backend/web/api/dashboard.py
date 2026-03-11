from fastapi import APIRouter, Depends

from web.auth.dependencies import get_current_user
from web.auth.guards import is_admin
from db import get_connection


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats")
def dashboard_stats(current_user=Depends(get_current_user)):
    """
    Estadísticas reales del panel: usuarios, pedidos, saldo y ganancias.
    """
    if not is_admin(current_user):
        return {"detail": "No autorizado"}

    conn = get_connection()
    cur = conn.cursor()

    # -- Admins locales (excluye plataforma, identificada por users.role) --
    cur.execute("""
        SELECT COUNT(*) FROM admins a
        LEFT JOIN users u ON u.id = a.user_id
        WHERE u.role NOT IN ('PLATFORM_ADMIN', 'ADMIN_PLATFORM') OR u.role IS NULL
    """)
    total_admins = cur.fetchone()[0] or 0

    cur.execute("""
        SELECT COUNT(*) FROM admins a
        LEFT JOIN users u ON u.id = a.user_id
        WHERE (u.role NOT IN ('PLATFORM_ADMIN', 'ADMIN_PLATFORM') OR u.role IS NULL)
          AND a.status = 'APPROVED'
    """)
    admins_activos = cur.fetchone()[0] or 0

    cur.execute("""
        SELECT COUNT(*) FROM admins a
        LEFT JOIN users u ON u.id = a.user_id
        WHERE (u.role NOT IN ('PLATFORM_ADMIN', 'ADMIN_PLATFORM') OR u.role IS NULL)
          AND a.status = 'PENDING'
    """)
    admins_pendientes = cur.fetchone()[0] or 0

    # -- Repartidores --
    cur.execute("SELECT COUNT(*) FROM couriers")
    total_couriers = cur.fetchone()[0] or 0

    cur.execute("SELECT COUNT(*) FROM couriers WHERE status = 'APPROVED'")
    couriers_activos = cur.fetchone()[0] or 0

    cur.execute("SELECT COUNT(*) FROM couriers WHERE status = 'PENDING'")
    couriers_pendientes = cur.fetchone()[0] or 0

    # -- Aliados --
    cur.execute("SELECT COUNT(*) FROM allies")
    total_aliados = cur.fetchone()[0] or 0

    cur.execute("SELECT COUNT(*) FROM allies WHERE status = 'APPROVED'")
    aliados_activos = cur.fetchone()[0] or 0

    cur.execute("SELECT COUNT(*) FROM allies WHERE status = 'PENDING'")
    aliados_pendientes = cur.fetchone()[0] or 0

    # -- Pedidos --
    cur.execute("SELECT COUNT(*) FROM orders WHERE status IN ('PUBLISHED','ACCEPTED','PICKED_UP')")
    pedidos_activos = cur.fetchone()[0] or 0

    cur.execute("SELECT COUNT(*) FROM orders WHERE status = 'DELIVERED' AND DATE(delivered_at) = DATE('now')")
    pedidos_entregados_hoy = cur.fetchone()[0] or 0

    cur.execute("SELECT COUNT(*) FROM orders WHERE status = 'DELIVERED'")
    pedidos_total_entregados = cur.fetchone()[0] or 0

    # -- Saldo plataforma (admin cuyo users.role es PLATFORM_ADMIN) --
    cur.execute("""
        SELECT a.balance FROM admins a
        JOIN users u ON u.id = a.user_id
        WHERE u.role IN ('PLATFORM_ADMIN', 'ADMIN_PLATFORM')
        LIMIT 1
    """)
    row = cur.fetchone()
    saldo_plataforma = row[0] if row else 0

    # -- Ganancias (ledger FEE_INCOME este mes) --
    cur.execute("""
        SELECT COALESCE(SUM(amount), 0) FROM ledger
        WHERE kind IN ('FEE_INCOME', 'PLATFORM_FEE')
          AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')
    """)
    ganancias_mes = cur.fetchone()[0] or 0

    cur.execute("""
        SELECT COALESCE(SUM(amount), 0) FROM ledger
        WHERE kind IN ('FEE_INCOME', 'PLATFORM_FEE')
    """)
    ganancias_total = cur.fetchone()[0] or 0

    conn.close()

    return {
        "admins": {
            "total": total_admins,
            "activos": admins_activos,
            "pendientes": admins_pendientes,
        },
        "couriers": {
            "total": total_couriers,
            "activos": couriers_activos,
            "pendientes": couriers_pendientes,
        },
        "aliados": {
            "total": total_aliados,
            "activos": aliados_activos,
            "pendientes": aliados_pendientes,
        },
        "pedidos": {
            "activos": pedidos_activos,
            "entregados_hoy": pedidos_entregados_hoy,
            "total_entregados": pedidos_total_entregados,
        },
        "saldo_plataforma": saldo_plataforma,
        "ganancias_mes": ganancias_mes,
        "ganancias_total": ganancias_total,
    }
