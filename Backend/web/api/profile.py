"""
Endpoint de perfil accesible para todos los roles del panel web.
"""
from fastapi import APIRouter, Depends, HTTPException
from web.auth.dependencies import get_current_user
from web.users.models import UserRole

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("")
def get_profile(current_user=Depends(get_current_user)):
    """Retorna el perfil del usuario autenticado según su rol."""
    base = {
        "username": current_user.username,
        "role": current_user.role.value,
    }

    if current_user.role == UserRole.COURIER:
        if not current_user.courier_id:
            return {**base, "detail": None}
        from db import get_courier_web_profile
        detail = get_courier_web_profile(current_user.courier_id)
        return {**base, "detail": detail}

    if current_user.role in (UserRole.PLATFORM_ADMIN, UserRole.ADMIN_LOCAL):
        if not current_user.admin_id and current_user.role == UserRole.ADMIN_LOCAL:
            return {**base, "detail": None}
        from db import get_connection, P
        conn = get_connection()
        cur = conn.cursor()
        try:
            if current_user.role == UserRole.PLATFORM_ADMIN:
                cur.execute(
                    f"SELECT id, full_name, phone, city FROM admins WHERE is_platform_admin = 1 LIMIT 1"
                )
            else:
                cur.execute(
                    f"SELECT id, full_name, phone, city FROM admins WHERE id = {P}",
                    (current_user.admin_id,)
                )
            row = cur.fetchone()
            if not row:
                return {**base, "detail": None}
            if isinstance(row, dict):
                detail = {"id": row["id"], "full_name": row["full_name"],
                          "phone": row["phone"], "city": row["city"]}
            else:
                detail = {"id": row[0], "full_name": row[1], "phone": row[2], "city": row[3]}
            return {**base, "detail": detail}
        finally:
            conn.close()

    return base
