import os
import tempfile
import unittest

import db
import services


class DashboardServicesTests(unittest.TestCase):
    def setUp(self):
        fd, path = tempfile.mkstemp(prefix="domi_dashboard_", suffix=".db")
        os.close(fd)
        self.db_path = path
        os.environ["DB_PATH"] = self.db_path
        os.environ.pop("DATABASE_URL", None)
        db.init_db()

        self.platform_admin_id = self._seed_platform_admin()
        self.local_admin_id = self._seed_local_admin()
        self._seed_courier()
        self._seed_ally()
        self._seed_orders()
        self._seed_ledger()

    def tearDown(self):
        try:
            os.remove(self.db_path)
        except FileNotFoundError:
            pass

    def _seed_platform_admin(self):
        user = db.ensure_user(930001, "platform_admin")
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE users SET role = 'PLATFORM_ADMIN' WHERE id = ?", (user["id"],))
        cur.execute(
            """
            INSERT INTO admins (user_id, full_name, phone, city, barrio, status, team_name, team_code, balance)
            VALUES (?, ?, ?, ?, ?, 'APPROVED', ?, 'PLATFORM', ?)
            """,
            (user["id"], "Platform", "3000002001", "Pereira", "Centro", "PLATAFORMA", 2500),
        )
        admin_id = cur.lastrowid
        conn.commit()
        conn.close()
        return admin_id

    def _seed_local_admin(self):
        user = db.ensure_user(930002, "local_admin")
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO admins (user_id, full_name, phone, city, barrio, status, team_name, team_code, balance)
            VALUES (?, ?, ?, ?, ?, 'APPROVED', ?, 'TEAM3', ?)
            """,
            (user["id"], "Local", "3000002002", "Pereira", "Cuba", "Equipo Tres", 1000),
        )
        admin_id = cur.lastrowid
        conn.commit()
        conn.close()
        return admin_id

    def _seed_courier(self):
        user = db.ensure_user(930003, "courier_user")
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO couriers (user_id, full_name, id_number, phone, city, barrio, status, code)
            VALUES (?, ?, ?, ?, ?, ?, 'APPROVED', ?)
            """,
            (user["id"], "Courier Uno", "CC9300", "3110002001", "Pereira", "Centro", "R-9300"),
        )
        conn.commit()
        conn.close()

    def _seed_ally(self):
        user = db.ensure_user(930004, "ally_user")
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO allies (user_id, business_name, owner_name, address, city, barrio, phone, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING')
            """,
            (user["id"], "Tienda Dashboard", "Owner", "Cra 1", "Pereira", "Centro", "3100002001"),
        )
        conn.commit()
        conn.close()

    def _seed_orders(self):
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO orders (
                ally_id, status, customer_name, customer_phone, customer_address,
                customer_city, customer_barrio, total_fee
            )
            VALUES (?, 'PUBLISHED', ?, ?, ?, ?, ?, ?)
            """,
            (1, "Cliente A", "3200002001", "Dir A", "Pereira", "Centro", 5000),
        )
        cur.execute(
            """
            INSERT INTO orders (
                ally_id, status, customer_name, customer_phone, customer_address,
                customer_city, customer_barrio, total_fee, delivered_at
            )
            VALUES (?, 'DELIVERED', ?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (1, "Cliente B", "3200002002", "Dir B", "Pereira", "Centro", 7000),
        )
        conn.commit()
        conn.close()

    def _seed_ledger(self):
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO ledger (kind, from_type, from_id, to_type, to_id, amount, ref_type, ref_id, note)
            VALUES ('FEE_INCOME', 'ALLY', 1, 'ADMIN', ?, 200, 'ORDER', 1, 'fee ally')
            """,
            (self.local_admin_id,),
        )
        cur.execute(
            """
            INSERT INTO ledger (kind, from_type, from_id, to_type, to_id, amount, ref_type, ref_id, note)
            VALUES ('PLATFORM_FEE', 'COURIER', 1, 'ADMIN', ?, 100, 'ORDER', 1, 'fee platform')
            """,
            (self.platform_admin_id,),
        )
        conn.commit()
        conn.close()

    def test_get_dashboard_stats_returns_expected_contract(self):
        stats = services.get_dashboard_stats()

        self.assertEqual(1, stats["admins"]["total"])
        self.assertEqual(1, stats["admins"]["activos"])
        self.assertEqual(1, stats["couriers"]["total"])
        self.assertEqual(1, stats["couriers"]["activos"])
        self.assertEqual(1, stats["aliados"]["total"])
        self.assertEqual(1, stats["aliados"]["pendientes"])
        self.assertEqual(1, stats["pedidos"]["activos"])
        self.assertEqual(1, stats["pedidos"]["entregados_hoy"])
        self.assertEqual(1, stats["pedidos"]["total_entregados"])
        self.assertEqual(2500, stats["saldo_plataforma"])
        self.assertEqual(300, stats["ganancias_mes"])
        self.assertEqual(300, stats["ganancias_total"])


if __name__ == "__main__":
    unittest.main()
