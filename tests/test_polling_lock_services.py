import sys
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "Backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import services


class _DummyCursor:
    def __init__(self, row):
        self.row = row
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchone(self):
        return self.row


class _DummyConnection:
    def __init__(self, row):
        self.cursor_obj = _DummyCursor(row)
        self.closed = False

    def cursor(self):
        return self.cursor_obj

    def close(self):
        self.closed = True


class PollingLockServicesTests(unittest.TestCase):
    def test_bot_polling_lock_supported_only_for_postgres(self):
        with patch.object(services, "DB_ENGINE", "postgres"):
            self.assertTrue(services.bot_polling_lock_supported())
        with patch.object(services, "DB_ENGINE", "sqlite"):
            self.assertFalse(services.bot_polling_lock_supported())

    def test_try_acquire_bot_polling_lock_returns_connection_when_available(self):
        conn = _DummyConnection({"locked": True})
        with patch.object(services, "DB_ENGINE", "postgres"), \
             patch.object(services, "get_connection", return_value=conn):
            lock_conn = services.try_acquire_bot_polling_lock()

        self.assertIs(lock_conn, conn)
        self.assertFalse(conn.closed)
        self.assertEqual(
            ("SELECT pg_try_advisory_lock(%s) AS locked", (services.BOT_POLLING_LOCK_ID,)),
            conn.cursor_obj.executed[0],
        )

    def test_try_acquire_bot_polling_lock_closes_connection_when_busy(self):
        conn = _DummyConnection({"locked": False})
        with patch.object(services, "DB_ENGINE", "postgres"), \
             patch.object(services, "get_connection", return_value=conn):
            lock_conn = services.try_acquire_bot_polling_lock()

        self.assertIsNone(lock_conn)
        self.assertTrue(conn.closed)

    def test_release_bot_polling_lock_unlocks_and_closes_connection(self):
        conn = _DummyConnection({"locked": True})
        with patch.object(services, "DB_ENGINE", "postgres"):
            services.release_bot_polling_lock(conn)

        self.assertTrue(conn.closed)
        self.assertEqual(
            ("SELECT pg_advisory_unlock(%s)", (services.BOT_POLLING_LOCK_ID,)),
            conn.cursor_obj.executed[0],
        )


if __name__ == "__main__":
    unittest.main()
