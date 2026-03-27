"""Tests para web.users.repository con BD temporal."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Backend"))

import db
from web.users.models import UserRole, UserStatus
from web.users.repository import get_web_user_by_username, get_user_by_id, list_users


class WebUserRepositoryTests(unittest.TestCase):
    def setUp(self):
        fd, path = tempfile.mkstemp(prefix="domi_web_user_repo_", suffix=".db")
        os.close(fd)
        self.db_path = path
        os.environ["DB_PATH"] = self.db_path
        os.environ.pop("DATABASE_URL", None)
        os.environ["WEB_ADMIN_USER"] = "panel_admin"
        os.environ["WEB_ADMIN_PASSWORD"] = "test1234"
        db.init_db()
        # Insertar usuario directamente (evita dependencia de bcrypt en tests)
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO web_users (username, password_hash, role, status)
            VALUES (?, ?, 'ADMIN_PLATFORM', 'APPROVED')
            """,
            ("panel_admin", "hashed_test"),
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        try:
            os.remove(self.db_path)
        except (FileNotFoundError, PermissionError):
            pass

    def test_get_web_user_by_username_retorna_usuario_existente(self):
        user = get_web_user_by_username("panel_admin")

        self.assertIsNotNone(user)
        self.assertEqual("panel_admin", user.username)
        self.assertEqual(UserRole.PLATFORM_ADMIN, user.role)
        self.assertEqual(UserStatus.APPROVED, user.status)

    def test_get_web_user_by_username_retorna_none_si_no_existe(self):
        user = get_web_user_by_username("usuario_inexistente")

        self.assertIsNone(user)

    def test_get_user_by_id_retorna_usuario_correcto(self):
        created = get_web_user_by_username("panel_admin")
        self.assertIsNotNone(created)

        user = get_user_by_id(created.id)

        self.assertIsNotNone(user)
        self.assertEqual(created.id, user.id)
        self.assertEqual("panel_admin", user.username)

    def test_get_user_by_id_retorna_none_si_no_existe(self):
        self.assertIsNone(get_user_by_id(99999))

    def test_list_users_incluye_admin_inicial(self):
        users = list_users()

        self.assertGreaterEqual(len(users), 1)
        usernames = [u.username for u in users]
        self.assertIn("panel_admin", usernames)


if __name__ == "__main__":
    unittest.main()
