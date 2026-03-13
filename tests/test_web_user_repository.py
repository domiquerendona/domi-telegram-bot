import os
import unittest

from web.users.models import UserRole, UserStatus
from web.users.repository import get_configured_web_user, get_user_by_id, list_users


class WebUserRepositoryTests(unittest.TestCase):
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

    def test_get_configured_web_user_resolves_environment_identity(self):
        user = get_configured_web_user()

        self.assertEqual(77, user.id)
        self.assertEqual("panel_admin", user.username)
        self.assertEqual(UserRole.ADMIN_LOCAL, user.role)
        self.assertEqual(UserStatus.APPROVED, user.status)

    def test_list_users_returns_only_configured_web_user(self):
        users = list_users()

        self.assertEqual(1, len(users))
        self.assertEqual(77, users[0].id)
        self.assertEqual("panel_admin", users[0].username)

    def test_get_user_by_id_matches_configured_identity(self):
        self.assertIsNotNone(get_user_by_id(77))
        self.assertIsNone(get_user_by_id(999))


if __name__ == "__main__":
    unittest.main()
