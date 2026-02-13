import os
import tempfile
import threading
import unittest

import db
import services


class RechargeIdempotencyTests(unittest.TestCase):
    def setUp(self):
        fd, path = tempfile.mkstemp(prefix="domi_recharge_test_", suffix=".db")
        os.close(fd)
        self.db_path = path
        os.environ["DB_PATH"] = self.db_path
        os.environ.pop("DATABASE_URL", None)
        db.init_db()

        self.platform_admin_id, self.local_admin_id = self._seed_admins()
        self.courier_id = self._seed_courier()
        self._link_courier_to_local_admin(self.courier_id, self.local_admin_id)

    def tearDown(self):
        try:
            os.remove(self.db_path)
        except FileNotFoundError:
            pass

    def _seed_admins(self):
        platform_user = db.ensure_user(900001, "platform_admin")
        local_user = db.ensure_user(900002, "local_admin")

        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO admins (user_id, full_name, phone, city, barrio, status, team_name, team_code, balance)
            VALUES (?, ?, ?, ?, ?, 'APPROVED', ?, 'PLATFORM', ?)
            """,
            (platform_user["id"], "Platform", "3000000001", "Pereira", "Centro", "Plataforma", 100000),
        )
        platform_admin_id = cur.lastrowid

        cur.execute(
            """
            INSERT INTO admins (user_id, full_name, phone, city, barrio, status, team_name, team_code, balance)
            VALUES (?, ?, ?, ?, ?, 'APPROVED', ?, 'TEAM1', ?)
            """,
            (local_user["id"], "Local", "3000000002", "Pereira", "Cuba", "Los Panchos", 100000),
        )
        local_admin_id = cur.lastrowid
        conn.commit()
        conn.close()
        return platform_admin_id, local_admin_id

    def _seed_courier(self):
        courier_user = db.ensure_user(900003, "courier_one")
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO couriers (user_id, full_name, id_number, phone, city, barrio, status, code)
            VALUES (?, ?, ?, ?, ?, ?, 'APPROVED', ?)
            """,
            (courier_user["id"], "Courier One", "CC100", "3110000000", "Pereira", "Centro", "R-9003"),
        )
        courier_id = cur.lastrowid
        conn.commit()
        conn.close()
        return courier_id

    def _link_courier_to_local_admin(self, courier_id, admin_id):
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO admin_couriers (admin_id, courier_id, status, balance, created_at, updated_at)
            VALUES (?, ?, 'APPROVED', 0, datetime('now'), datetime('now'))
            """,
            (admin_id, courier_id),
        )
        conn.commit()
        conn.close()

    def _create_recharge_request(self, amount=10000):
        requester = db.ensure_user(900010, "requester")
        return db.create_recharge_request(
            target_type="COURIER",
            target_id=self.courier_id,
            admin_id=self.local_admin_id,
            amount=amount,
            requested_by_user_id=requester["id"],
            method="BANK",
            note="test",
            proof_file_id=f"proof_{amount}_{threading.get_ident()}",
        )

    @staticmethod
    def _run_in_parallel(fn_a, fn_b):
        barrier = threading.Barrier(2)
        out = {}

        def wrapped(name, fn):
            barrier.wait()
            out[name] = fn()

        t1 = threading.Thread(target=wrapped, args=("a", fn_a))
        t2 = threading.Thread(target=wrapped, args=("b", fn_b))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        return out

    def test_approve_is_idempotent_under_concurrency(self):
        request_id = self._create_recharge_request(amount=12000)

        out = self._run_in_parallel(
            lambda: services.approve_recharge_request(request_id, self.local_admin_id),
            lambda: services.approve_recharge_request(request_id, self.local_admin_id),
        )

        successes = [res for res in out.values() if res[0] is True]
        failures = [res for res in out.values() if res[0] is False]
        self.assertEqual(1, len(successes))
        self.assertEqual(1, len(failures))

        req = db.get_recharge_request(request_id)
        self.assertEqual("APPROVED", req[5])

        courier_balance = db.get_courier_link_balance(self.courier_id, self.local_admin_id)
        self.assertEqual(12000, courier_balance)

        local_admin_balance = db.get_admin_balance(self.local_admin_id)
        self.assertEqual(88000, local_admin_balance)

        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT COUNT(*) FROM ledger
            WHERE ref_type = 'RECHARGE_REQUEST' AND ref_id = ?
            """,
            (request_id,),
        )
        ledger_count = cur.fetchone()[0]
        conn.close()
        self.assertEqual(2, ledger_count)

    def test_reject_is_idempotent_under_concurrency(self):
        request_id = self._create_recharge_request(amount=7000)

        out = self._run_in_parallel(
            lambda: services.reject_recharge_request(request_id, self.local_admin_id),
            lambda: services.reject_recharge_request(request_id, self.local_admin_id),
        )

        successes = [res for res in out.values() if res[0] is True]
        failures = [res for res in out.values() if res[0] is False]
        self.assertEqual(1, len(successes))
        self.assertEqual(1, len(failures))

        req = db.get_recharge_request(request_id)
        self.assertEqual("REJECTED", req[5])

        courier_balance = db.get_courier_link_balance(self.courier_id, self.local_admin_id)
        self.assertEqual(0, courier_balance)

    def test_approve_vs_reject_race_only_one_wins(self):
        request_id = self._create_recharge_request(amount=5000)

        out = self._run_in_parallel(
            lambda: services.approve_recharge_request(request_id, self.local_admin_id),
            lambda: services.reject_recharge_request(request_id, self.local_admin_id),
        )

        successes = [res for res in out.values() if res[0] is True]
        failures = [res for res in out.values() if res[0] is False]
        self.assertEqual(1, len(successes))
        self.assertEqual(1, len(failures))

        req = db.get_recharge_request(request_id)
        final_status = req[5]
        self.assertIn(final_status, ("APPROVED", "REJECTED"))

        courier_balance = db.get_courier_link_balance(self.courier_id, self.local_admin_id)
        if final_status == "APPROVED":
            self.assertEqual(5000, courier_balance)
        else:
            self.assertEqual(0, courier_balance)


if __name__ == "__main__":
    unittest.main()
