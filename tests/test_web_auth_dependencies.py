import os
import sys
import types
import unittest
from unittest.mock import patch

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

    def Depends(dependency=None):
        return dependency

    fastapi_stub.HTTPException = HTTPException
    fastapi_stub.Header = Header
    fastapi_stub.Depends = Depends
    sys.modules["fastapi"] = fastapi_stub

HTTPException = fastapi_stub.HTTPException

from web.auth.dependencies import get_current_user
from web.auth.token import create_token
from web.users.models import UserRole, UserStatus
from web.users.repository import WebUser


class WebAuthDependenciesTests(unittest.TestCase):

    def test_get_current_user_resolves_configured_identity(self):
        token = create_token("panel_admin")
        fake_user = WebUser(id=77, username="panel_admin",
                            role=UserRole.ADMIN_LOCAL, status=UserStatus.APPROVED)

        with patch("web.auth.dependencies.get_web_user_by_username", return_value=fake_user):
            current_user = get_current_user(f"Bearer {token}")

        self.assertEqual(77, current_user.id)
        self.assertEqual("panel_admin", current_user.username)
        self.assertEqual(UserRole.ADMIN_LOCAL, current_user.role)
        self.assertEqual(UserStatus.APPROVED, current_user.status)

    def test_get_current_user_rejects_unknown_authenticated_username(self):
        token = create_token("otro_usuario")

        with patch("web.auth.dependencies.get_web_user_by_username", return_value=None):
            with self.assertRaises(HTTPException) as ctx:
                get_current_user(f"Bearer {token}")

        self.assertEqual(401, ctx.exception.status_code)


if __name__ == "__main__":
    unittest.main()
