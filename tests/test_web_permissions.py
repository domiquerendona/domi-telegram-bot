import sys
import types
import unittest
from unittest.mock import patch

fastapi_stub = sys.modules.get("fastapi")
if fastapi_stub is None:
    fastapi_stub = types.ModuleType("fastapi")
    sys.modules["fastapi"] = fastapi_stub


if not hasattr(fastapi_stub, "HTTPException"):
    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str):
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    fastapi_stub.HTTPException = HTTPException


if not hasattr(fastapi_stub, "APIRouter"):
    class APIRouter:
        def __init__(self, *args, **kwargs):
            pass

        def get(self, *args, **kwargs):
            def decorator(fn):
                return fn
            return decorator

        def post(self, *args, **kwargs):
            def decorator(fn):
                return fn
            return decorator

    fastapi_stub.APIRouter = APIRouter


if not hasattr(fastapi_stub, "Depends"):
    def Depends(dependency):
        return dependency

    fastapi_stub.Depends = Depends


if not hasattr(fastapi_stub, "Header"):
    fastapi_stub.Header = lambda default="": default


HTTPException = fastapi_stub.HTTPException

from web.api.dashboard import dashboard_stats
from web.auth.guards import require_panel_access, require_panel_admin
from web.users.models import UserRole, UserStatus
from web.users.repository import WebUser


class WebPermissionsTests(unittest.TestCase):
    def _user(self, role: UserRole, status: UserStatus):
        return WebUser(id=77, username="panel_admin", role=role, status=status)

    def test_require_panel_admin_allows_approved_admin(self):
        user = self._user(UserRole.ADMIN_LOCAL, UserStatus.APPROVED)

        resolved = require_panel_admin(user)

        self.assertIs(user, resolved)

    def test_require_panel_admin_rejects_invalid_role(self):
        user = self._user(UserRole.COURIER, UserStatus.APPROVED)

        with self.assertRaises(HTTPException) as ctx:
            require_panel_admin(user)

        self.assertEqual(403, ctx.exception.status_code)
        self.assertEqual("No autorizado", ctx.exception.detail)

    def test_require_panel_access_rejects_invalid_status(self):
        user = self._user(UserRole.PLATFORM_ADMIN, UserStatus.INACTIVE)

        with self.assertRaises(HTTPException) as ctx:
            require_panel_access(user)

        self.assertEqual(403, ctx.exception.status_code)
        self.assertEqual("Usuario bloqueado", ctx.exception.detail)

    def test_dashboard_stats_requires_admin_and_returns_data(self):
        user = self._user(UserRole.PLATFORM_ADMIN, UserStatus.APPROVED)

        with patch("web.api.dashboard.get_dashboard_stats", return_value={"ok": True}) as mocked:
            response = dashboard_stats(current_user=user)

        mocked.assert_called_once_with()
        self.assertEqual({"ok": True}, response)


if __name__ == "__main__":
    unittest.main()
