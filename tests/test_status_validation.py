import os
import tempfile
import unittest

import db


class RoleStatusValidationTests(unittest.TestCase):
    def setUp(self):
        fd, path = tempfile.mkstemp(prefix="domi_status_test_", suffix=".db")
        os.close(fd)
        self.db_path = path
        os.environ["DB_PATH"] = self.db_path
        os.environ.pop("DATABASE_URL", None)
        db.init_db()

        self.admin_id = self._seed_admin()
        self.courier_id = self._seed_courier()
        self.request_id = self._seed_recharge_request()

    def tearDown(self):
        try:
            os.remove(self.db_path)
        except FileNotFoundError:
            pass

    def _seed_admin(self):
        admin_user = db.ensure_user(910001, "status_admin")
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO admins (user_id, full_name, phone, city, barrio, status, team_name, team_code, balance)
            VALUES (?, ?, ?, ?, ?, 'APPROVED', ?, 'TEAM_STATUS', ?)
            """,
            (admin_user["id"], "Status Admin", "3001111111", "Pereira", "Centro", "Team Status", 100000),
        )
        admin_id = cur.lastrowid
        conn.commit()
        conn.close()
        return admin_id

    def _seed_courier(self):
        courier_user = db.ensure_user(910002, "status_courier")
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO couriers (user_id, full_name, id_number, phone, city, barrio, status, code)
            VALUES (?, ?, ?, ?, ?, ?, 'APPROVED', ?)
            """,
            (courier_user["id"], "Status Courier", "CC9100", "3111111111", "Pereira", "Cuba", "R-9100"),
        )
        courier_id = cur.lastrowid
        cur.execute(
            """
            INSERT INTO admin_couriers (admin_id, courier_id, status, balance, created_at, updated_at)
            VALUES (?, ?, 'APPROVED', 0, datetime('now'), datetime('now'))
            """,
            (self.admin_id, courier_id),
        )
        conn.commit()
        conn.close()
        return courier_id

    def _seed_recharge_request(self):
        requester = db.ensure_user(910003, "status_requester")
        return db.create_recharge_request(
            target_type="COURIER",
            target_id=self.courier_id,
            admin_id=self.admin_id,
            amount=5000,
            requested_by_user_id=requester["id"],
            method="BANK",
            note="status-test",
            proof_file_id="status-proof-910003",
        )

    def test_normalize_role_status_normalizes_valid_values(self):
        self.assertEqual("APPROVED", db.normalize_role_status("approved"))
        self.assertEqual("REJECTED", db.normalize_role_status("  rejected  "))
        self.assertEqual("INACTIVE", db.normalize_role_status("inactive"))
        self.assertEqual("PENDING", db.normalize_role_status("PENDING"))

    def test_normalize_role_status_rejects_invalid_values(self):
        invalid_values = [None, "", "   ", "ACTIVE", "PENDIENTE", "APPROVE"]
        for value in invalid_values:
            with self.assertRaises(ValueError):
                db.normalize_role_status(value)

    def test_update_recharge_status_rejects_invalid_state_without_write(self):
        with self.assertRaises(ValueError):
            db.update_recharge_status(self.request_id, "INVALID", self.admin_id)

        req = db.get_recharge_request(self.request_id)
        self.assertEqual("PENDING", req["status"])

    def test_update_recharge_status_accepts_lowercase_and_persists_normalized(self):
        db.update_recharge_status(self.request_id, "approved", self.admin_id)
        req = db.get_recharge_request(self.request_id)
        self.assertEqual("APPROVED", req["status"])


if __name__ == "__main__":
    unittest.main()
