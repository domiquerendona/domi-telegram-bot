import os
import tempfile
import unittest

import db
import services


class WebAdminServicesTests(unittest.TestCase):
    def setUp(self):
        fd, path = tempfile.mkstemp(prefix="domi_web_admin_", suffix=".db")
        os.close(fd)
        self.db_path = path
        os.environ["DB_PATH"] = self.db_path
        os.environ.pop("DATABASE_URL", None)
        db.init_db()

        self.platform_admin_id, self.local_admin_id = self._seed_admins()
        self.ally_id = self._seed_ally()
        self.courier_id = self._seed_courier()
        self._link_members()

    def tearDown(self):
        try:
            os.remove(self.db_path)
        except FileNotFoundError:
            pass

    def _seed_admins(self):
        platform_user = db.ensure_user(920001, "platform_admin")
        local_user = db.ensure_user(920002, "local_admin")
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO admins (user_id, full_name, phone, city, barrio, status, team_name, team_code, balance)
            VALUES (?, ?, ?, ?, ?, 'APPROVED', ?, 'PLATFORM', ?)
            """,
            (platform_user["id"], "Platform", "3000001001", "Pereira", "Centro", "Plataforma", 0),
        )
        platform_admin_id = cur.lastrowid
        cur.execute(
            """
            INSERT INTO admins (user_id, full_name, phone, city, barrio, status, team_name, team_code, balance)
            VALUES (?, ?, ?, ?, ?, 'APPROVED', ?, 'TEAM2', ?)
            """,
            (local_user["id"], "Local", "3000001002", "Pereira", "Cuba", "Equipo Dos", 0),
        )
        local_admin_id = cur.lastrowid
        conn.commit()
        conn.close()
        return platform_admin_id, local_admin_id

    def _seed_ally(self):
        ally_user = db.ensure_user(920003, "ally_user")
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO allies (user_id, business_name, owner_name, address, city, barrio, phone, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'APPROVED')
            """,
            (ally_user["id"], "Tienda Uno", "Owner Ally", "Calle 1", "Pereira", "Centro", "3100000001"),
        )
        ally_id = cur.lastrowid
        conn.commit()
        conn.close()
        return ally_id

    def _seed_courier(self):
        courier_user = db.ensure_user(920004, "courier_user")
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO couriers (user_id, full_name, id_number, phone, city, barrio, status, code)
            VALUES (?, ?, ?, ?, ?, ?, 'APPROVED', ?)
            """,
            (courier_user["id"], "Courier Uno", "CC9200", "3110000001", "Pereira", "Centro", "R-9200"),
        )
        courier_id = cur.lastrowid
        conn.commit()
        conn.close()
        return courier_id

    def _link_members(self):
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO admin_allies (admin_id, ally_id, status, balance, created_at, updated_at)
            VALUES (?, ?, 'APPROVED', 1000, datetime('now'), datetime('now'))
            """,
            (self.local_admin_id, self.ally_id),
        )
        cur.execute(
            """
            INSERT INTO admin_couriers (admin_id, courier_id, status, balance, created_at, updated_at)
            VALUES (?, ?, 'APPROVED', 1000, datetime('now'), datetime('now'))
            """,
            (self.local_admin_id, self.courier_id),
        )
        conn.commit()
        conn.close()

    def _create_order(self, status="PICKED_UP"):
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO orders (
                ally_id, courier_id, status, customer_name, customer_phone, customer_address,
                customer_city, customer_barrio, total_fee, courier_admin_id_snapshot
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self.ally_id,
                self.courier_id,
                status,
                "Cliente Uno",
                "3200000001",
                "Cra 10",
                "Pereira",
                "Centro",
                5000,
                self.local_admin_id,
            ),
        )
        order_id = cur.lastrowid
        conn.commit()
        conn.close()
        return order_id

    def _create_support_request(self, order_id):
        return db.create_order_support_request(
            courier_id=self.courier_id,
            admin_id=self.local_admin_id,
            order_id=order_id,
            route_id=None,
            route_seq=None,
        )

    def test_get_admin_panel_balances_returns_expected_structure(self):
        data = services.get_admin_panel_balances()
        self.assertIn("admins", data)
        self.assertIn("couriers", data)
        self.assertIn("aliados", data)
        admin_names = {row["nombre"] for row in data["admins"]}
        self.assertIn("Local", admin_names)

    def test_get_and_update_admin_panel_pricing_settings(self):
        before = services.get_admin_panel_pricing_settings()
        self.assertIn("pricing_precio_0_2km", before)

        services.update_admin_panel_pricing_settings({"pricing_precio_0_2km": 6100, "invalid_key": 999})
        after = services.get_admin_panel_pricing_settings()
        self.assertEqual("6100", after["pricing_precio_0_2km"])
        self.assertIsNone(after.get("invalid_key"))

    def test_cancel_order_from_admin_panel_cancels_order(self):
        order_id = self._create_order(status="ACCEPTED")
        previous_status = services.cancel_order_from_admin_panel(order_id)
        self.assertEqual("ACCEPTED", previous_status)

        order = db.get_order_by_id(order_id)
        self.assertEqual("CANCELLED", order["status"])

    def test_resolve_support_request_from_admin_panel_fin_marks_delivered_and_charges(self):
        order_id = self._create_order(status="PICKED_UP")
        support_id = self._create_support_request(order_id)

        resolved_order_id = services.resolve_support_request_from_admin_panel(
            support_id=support_id,
            action="fin",
            admin_db_id=self.local_admin_id,
        )

        self.assertEqual(order_id, resolved_order_id)

        order = db.get_order_by_id(order_id)
        self.assertEqual("DELIVERED", order["status"])

        req = db.get_support_request_full(support_id)
        self.assertEqual("RESOLVED", req["status"])
        self.assertEqual("DELIVERED", req["resolution"])

        self.assertEqual(700, db.get_ally_link_balance(self.ally_id, self.local_admin_id))
        self.assertEqual(700, db.get_courier_link_balance(self.courier_id, self.local_admin_id))
        self.assertEqual(400, db.get_admin_balance(self.local_admin_id))
        self.assertEqual(200, db.get_admin_balance(self.platform_admin_id))


if __name__ == "__main__":
    unittest.main()
