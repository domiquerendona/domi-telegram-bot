import os
import tempfile
import unittest

import db
import services


class ProfileChangeServicesTests(unittest.TestCase):
    def setUp(self):
        fd, path = tempfile.mkstemp(prefix="domi_profile_changes_", suffix=".db")
        os.close(fd)
        self.db_path = path
        os.environ["DB_PATH"] = self.db_path
        os.environ.pop("DATABASE_URL", None)
        db.init_db()

        self.admin_one_id, self.admin_two_id = self._seed_admins()
        self.courier_id = self._seed_courier()
        self.ally_id = self._seed_ally()
        self._link_courier_to_admin_one()

    def tearDown(self):
        try:
            os.remove(self.db_path)
        except FileNotFoundError:
            pass

    def _seed_admins(self):
        admin_user_one = db.ensure_user(930001, "admin_one")
        admin_user_two = db.ensure_user(930002, "admin_two")
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO admins (user_id, full_name, phone, city, barrio, status, team_name, team_code, balance)
            VALUES (?, ?, ?, ?, ?, 'APPROVED', ?, 'TEAM1', ?)
            """,
            (admin_user_one["id"], "Admin Uno", "3001111111", "Pereira", "Centro", "Equipo Uno", 0),
        )
        admin_one_id = cur.lastrowid
        cur.execute(
            """
            INSERT INTO admins (user_id, full_name, phone, city, barrio, status, team_name, team_code, balance)
            VALUES (?, ?, ?, ?, ?, 'APPROVED', ?, 'TEAM2', ?)
            """,
            (admin_user_two["id"], "Admin Dos", "3002222222", "Pereira", "Cuba", "Equipo Dos", 0),
        )
        admin_two_id = cur.lastrowid
        conn.commit()
        conn.close()
        return admin_one_id, admin_two_id

    def _seed_courier(self):
        courier_user = db.ensure_user(930003, "courier_profile")
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO couriers (user_id, full_name, id_number, phone, city, barrio, status, code)
            VALUES (?, ?, ?, ?, ?, ?, 'APPROVED', ?)
            """,
            (courier_user["id"], "Courier Perfil", "CC9300", "3110000001", "Pereira", "Centro", "R-9300"),
        )
        courier_id = cur.lastrowid
        conn.commit()
        conn.close()
        return courier_id

    def _seed_ally(self):
        ally_user = db.ensure_user(930004, "ally_profile")
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO allies (user_id, business_name, owner_name, address, city, barrio, phone, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'APPROVED')
            """,
            (ally_user["id"], "Aliado Perfil", "Owner Perfil", "Cra 1", "Pereira", "Centro", "3120000001"),
        )
        ally_id = cur.lastrowid
        conn.commit()
        conn.close()
        return ally_id

    def _link_courier_to_admin_one(self):
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO admin_couriers (admin_id, courier_id, status, balance, created_at, updated_at)
            VALUES (?, ?, 'APPROVED', 0, datetime('now'), datetime('now'))
            """,
            (self.admin_one_id, self.courier_id),
        )
        conn.commit()
        conn.close()

    def test_apply_profile_change_request_update_updates_admin_phone(self):
        request_row = {
            "target_role": "admin",
            "target_role_id": self.admin_one_id,
            "field_name": "phone",
            "new_value": "3009999999",
            "new_lat": None,
            "new_lng": None,
        }

        services.apply_profile_change_request_update(request_row)

        admin = db.get_admin_by_id(self.admin_one_id)
        self.assertEqual("3009999999", admin["phone"])

    def test_apply_profile_change_request_update_creates_default_ally_location(self):
        request_row = {
            "target_role": "ally",
            "target_role_id": self.ally_id,
            "field_name": "ally_default_location",
            "new_value": "Cra 9 #10-20",
            "new_lat": 4.8133,
            "new_lng": -75.6961,
        }

        services.apply_profile_change_request_update(request_row)

        location = db.get_default_ally_location(self.ally_id)
        self.assertIsNotNone(location)
        self.assertEqual("Cra 9 #10-20", location["address"])
        self.assertEqual(4.8133, location["lat"])
        self.assertEqual(-75.6961, location["lng"])

    def test_apply_profile_change_request_update_migrates_courier_admin_team(self):
        request_row = {
            "target_role": "courier",
            "target_role_id": self.courier_id,
            "field_name": "admin_team_code",
            "new_value": "team2",
            "new_lat": None,
            "new_lng": None,
        }

        services.apply_profile_change_request_update(request_row)

        link = db.get_admin_link_for_courier(self.courier_id)
        self.assertIsNotNone(link)
        self.assertEqual(self.admin_two_id, link["admin_id"])

        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT status
            FROM admin_couriers
            WHERE admin_id = ? AND courier_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (self.admin_one_id, self.courier_id),
        )
        old_link = cur.fetchone()
        conn.close()
        self.assertIsNotNone(old_link)
        self.assertEqual("INACTIVE", old_link["status"])


if __name__ == "__main__":
    unittest.main()
