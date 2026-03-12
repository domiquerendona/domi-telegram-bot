import os
import tempfile
import unittest

import db
import services


class MainNotificationServicesTests(unittest.TestCase):
    def setUp(self):
        fd, path = tempfile.mkstemp(prefix="domi_main_notifications_", suffix=".db")
        os.close(fd)
        self.db_path = path
        os.environ["DB_PATH"] = self.db_path
        os.environ.pop("DATABASE_URL", None)
        db.init_db()
        self.courier_id, self.ally_id = self._seed_members()

    def tearDown(self):
        try:
            os.remove(self.db_path)
        except FileNotFoundError:
            pass

    def _seed_members(self):
        courier_user = db.ensure_user(940001, "courier_notify")
        ally_user = db.ensure_user(940002, "ally_notify")

        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO couriers (user_id, full_name, id_number, phone, city, barrio, status, code)
            VALUES (?, ?, ?, ?, ?, ?, 'PENDING', ?)
            """,
            (courier_user["id"], "Courier Notify", "CC9400", "3110000009", "Pereira", "Centro", "R-9400"),
        )
        courier_id = cur.lastrowid

        cur.execute(
            """
            INSERT INTO allies (user_id, business_name, owner_name, address, city, barrio, phone, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING')
            """,
            (ally_user["id"], "Aliado Notify", "Owner Notify", "Cra 40", "Pereira", "Centro", "3120000009"),
        )
        ally_id = cur.lastrowid
        conn.commit()
        conn.close()
        return courier_id, ally_id

    def test_get_courier_approval_notification_chat_id(self):
        self.assertEqual(
            940001,
            services.get_courier_approval_notification_chat_id(self.courier_id),
        )

    def test_get_ally_approval_notification_chat_id(self):
        self.assertEqual(
            940002,
            services.get_ally_approval_notification_chat_id(self.ally_id),
        )


if __name__ == "__main__":
    unittest.main()
