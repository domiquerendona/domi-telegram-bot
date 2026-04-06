from dataclasses import dataclass
from typing import Optional

from web.users.models import UserRole, UserStatus


@dataclass
class WebUser:
    id: int
    username: str
    role: UserRole
    status: UserStatus
    admin_id: Optional[int] = None    # admins.id del equipo; None para PLATFORM_ADMIN
    courier_id: Optional[int] = None  # couriers.id; solo para rol COURIER
    created_at: Optional[str] = None  # fecha de creación del usuario del panel


def _row_to_web_user(row) -> Optional["WebUser"]:
    if row is None:
        return None
    if isinstance(row, dict):
        return WebUser(
            id=row["id"],
            username=row["username"],
            role=UserRole(row["role"]),
            status=UserStatus(row["status"]),
            admin_id=row.get("admin_id"),
            courier_id=row.get("courier_id"),
            created_at=str(row["created_at"]) if row.get("created_at") else None,
        )
    # SQLite row por índice: id, username, password_hash, role, status, admin_id, courier_id, created_at
    return WebUser(
        id=row[0],
        username=row[1],
        role=UserRole(row[3]),
        status=UserStatus(row[4]),
        admin_id=row[5] if len(row) > 5 else None,
        courier_id=row[6] if len(row) > 6 else None,
        created_at=str(row[7]) if len(row) > 7 and row[7] else None,
    )


def get_web_user_by_username(username: str) -> Optional[WebUser]:
    """Retorna WebUser desde BD o None."""
    from db import get_web_user_by_username as _db_get
    return _row_to_web_user(_db_get(username))


def get_user_by_id(user_id: int) -> Optional[WebUser]:
    """Retorna WebUser desde BD o None."""
    from db import get_web_user_by_id as _db_get
    return _row_to_web_user(_db_get(user_id))


def list_users():
    """Lista todos los usuarios del panel web."""
    from db import list_web_users as _db_list
    result = []
    for row in _db_list():
        if isinstance(row, dict):
            result.append(WebUser(
                id=row["id"],
                username=row["username"],
                role=UserRole(row["role"]),
                status=UserStatus(row["status"]),
                admin_id=row.get("admin_id"),
            ))
        else:
            result.append(WebUser(
                id=row[0],
                username=row[1],
                role=UserRole(row[2]),
                status=UserStatus(row[3]),
                admin_id=row[4] if len(row) > 4 else None,
            ))
    return result
