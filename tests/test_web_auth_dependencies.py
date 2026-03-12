import os
import sys
import types
import unittest

fastapi_stub = sys.modules.get("fastapi")
if fastapi_stub is None:
    fastapi_stub = types.ModuleType("fastapi")

    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str):
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    def Header(default=""):
        return default

    fastapi_stub.HTTPException = HTTPException
    fastapi_stub.Header = Header
    sys.modules["fastapi"] = fastapi_stub

HTTPException = fastapi_stub.HTTPException

from web.auth.dependencies import get_current_user
from web.auth.token import create_token
from web.users.models import UserRole, UserStatus


class WebAuthDependenciesTests(unittest.TestCase):
    def setUp(self):
        self._original = {
            "WEB_ADMIN_USER": os.environ.get("WEB_ADMIN_USER"),
            "WEB_ADMIN_ID": os.environ.get("WEB_ADMIN_ID"),
            "WEB_ADMIN_ROLE": os.environ.get("WEB_ADMIN_ROLE"),
            "WEB_ADMIN_STATUS": os.environ.get("WEB_ADMIN_STATUS"),
        }
        os.environ["WEB_ADMIN_USER"] = "panel_admin"
        os.environ["WEB_ADMIN_ID"] = "77"
        os.environ["WEB_ADMIN_ROLE"] = "ADMIN_LOCAL"
        os.environ["WEB_ADMIN_STATUS"] = "APPROVED"

    def tearDown(self):
        for key, value in self._original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_get_current_user_resolves_configured_identity(self):
        token = create_token("panel_admin")

        current_user = get_current_user(f"Bearer {token}")

        self.assertEqual(77, current_user.id)
        self.assertEqual("panel_admin", current_user.username)
        self.assertEqual(UserRole.ADMIN_LOCAL, current_user.role)
        self.assertEqual(UserStatus.APPROVED, current_user.status)

    def test_get_current_user_rejects_unknown_authenticated_username(self):
        token = create_token("otro_usuario")

        with self.assertRaises(HTTPException) as ctx:
            get_current_user(f"Bearer {token}")

        self.assertEqual(401, ctx.exception.status_code)


if __name__ == "__main__":
    unittest.main()
