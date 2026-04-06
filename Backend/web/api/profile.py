"""
Endpoints de perfil accesibles para todos los roles del panel web.
"""
import bcrypt
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
        "created_at": current_user.created_at,
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
                    "SELECT id, full_name, phone, city FROM admins WHERE team_code = 'PLATFORM' AND is_deleted = 0 LIMIT 1"
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
        except Exception:
            return {**base, "detail": None}
        finally:
            conn.close()

    return base


@router.patch("/password")
def change_password(payload: dict, current_user=Depends(get_current_user)):
    """Cambia la contraseña del usuario autenticado."""
    current_password = (payload.get("current_password") or "").strip()
    new_password = (payload.get("new_password") or "").strip()

    if not current_password or not new_password:
        raise HTTPException(status_code=400, detail="Debes enviar current_password y new_password")
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="La nueva contraseña debe tener al menos 6 caracteres")

    # Verificar contraseña actual
    from db import get_web_user_by_id, update_web_user_password
    row = get_web_user_by_id(current_user.id)
    if row is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    stored_hash = row["password_hash"] if isinstance(row, dict) else row[2]
    if not bcrypt.checkpw(current_password.encode(), stored_hash.encode()):
        raise HTTPException(status_code=400, detail="Contraseña actual incorrecta")

    new_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    update_web_user_password(current_user.id, new_hash)
    return {"ok": True}


@router.patch("/detail")
def update_detail(payload: dict, current_user=Depends(get_current_user)):
    """Actualiza nombre y teléfono del perfil del usuario autenticado."""
    full_name = (payload.get("full_name") or "").strip()
    phone = (payload.get("phone") or "").strip()

    if not full_name:
        raise HTTPException(status_code=400, detail="El nombre no puede estar vacío")

    from db import update_admin_name_phone, update_courier_name_phone

    if current_user.role == UserRole.COURIER:
        if not current_user.courier_id:
            raise HTTPException(status_code=400, detail="Sin perfil de courier vinculado")
        update_courier_name_phone(current_user.courier_id, full_name, phone)
    elif current_user.role in (UserRole.PLATFORM_ADMIN, UserRole.ADMIN_LOCAL):
        if not current_user.admin_id and current_user.role == UserRole.ADMIN_LOCAL:
            raise HTTPException(status_code=400, detail="Sin perfil de admin vinculado")
        # Para PLATFORM_ADMIN buscamos su admin_id desde la BD
        entity_id = current_user.admin_id
        if current_user.role == UserRole.PLATFORM_ADMIN and not entity_id:
            from db import get_connection, P
            conn = get_connection()
            cur = conn.cursor()
            try:
                cur.execute("SELECT id FROM admins WHERE team_code = 'PLATFORM' AND is_deleted = 0 LIMIT 1")
                row = cur.fetchone()
                entity_id = (row["id"] if isinstance(row, dict) else row[0]) if row else None
            finally:
                conn.close()
        if not entity_id:
            raise HTTPException(status_code=400, detail="Sin perfil de admin vinculado")
        update_admin_name_phone(entity_id, full_name, phone)
    else:
        raise HTTPException(status_code=400, detail="Rol no soportado")

    return {"ok": True}


@router.get("/activity")
def get_activity(current_user=Depends(get_current_user)):
    """Retorna actividad reciente del usuario autenticado."""
    from db import get_admin_recent_activity, get_courier_recent_activity

    if current_user.role == UserRole.COURIER:
        if not current_user.courier_id:
            return {"items": []}
        return {"items": get_courier_recent_activity(current_user.courier_id)}

    if current_user.role in (UserRole.PLATFORM_ADMIN, UserRole.ADMIN_LOCAL):
        admin_id = current_user.admin_id if current_user.role == UserRole.ADMIN_LOCAL else None
        return {"items": get_admin_recent_activity(admin_id)}

    return {"items": []}
