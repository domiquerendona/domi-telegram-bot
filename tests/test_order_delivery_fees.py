import os
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

telegram_stub = types.ModuleType("telegram")


class InlineKeyboardButton:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class InlineKeyboardMarkup:
    def __init__(self, keyboard):
        self.keyboard = keyboard


telegram_stub.InlineKeyboardButton = InlineKeyboardButton
telegram_stub.InlineKeyboardMarkup = InlineKeyboardMarkup
sys.modules.setdefault("telegram", telegram_stub)

import db
import order_delivery


class _DummyQuery:
    def __init__(self):
        self.messages = []

    def edit_message_text(self, text):
        self.messages.append(text)


class _DummyBot:
    def __init__(self):
        self.messages = []

    def send_message(self, chat_id, text):
        self.messages.append({"chat_id": chat_id, "text": text})


class _DummyUpdate:
    def __init__(self, telegram_id):
        self.callback_query = _DummyQuery()
        self.effective_user = types.SimpleNamespace(id=telegram_id)


class _DummyContext:
    def __init__(self):
        self.bot = _DummyBot()
        self.bot_data = {}


class OrderDeliveryFeeTests(unittest.TestCase):
    def setUp(self):
        fd, path = tempfile.mkstemp(prefix="domi_order_delivery_", suffix=".db")
        os.close(fd)
        self.db_path = path
        os.environ["DB_PATH"] = self.db_path
        os.environ.pop("DATABASE_URL", None)
        db.init_db()

        self.platform_admin_id, self.local_admin_id = self._seed_admins()
        self.ally_id = self._seed_ally()
        self.courier_id, self.courier_telegram_id = self._seed_courier()
        self._link_ally_to_local_admin(balance=1000)
        self._link_courier_to_local_admin(balance=1000)

    def tearDown(self):
        try:
            os.remove(self.db_path)
        except FileNotFoundError:
            pass

    def _seed_admins(self):
        platform_user = db.ensure_user(940001, "platform_admin")
        local_user = db.ensure_user(940002, "local_admin")
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO admins (user_id, full_name, phone, city, barrio, status, team_name, team_code, balance)
            VALUES (?, ?, ?, ?, ?, 'APPROVED', ?, 'TEAM0', ?)
            """,
            (platform_user["id"], "Platform", "3000000000", "Pereira", "Centro", "Plataforma", 0),
        )
        platform_admin_id = cur.lastrowid
        cur.execute("UPDATE admins SET team_code = 'PLATFORM' WHERE id = ?", (platform_admin_id,))
        cur.execute(
            """
            INSERT INTO admins (user_id, full_name, phone, city, barrio, status, team_name, team_code, balance)
            VALUES (?, ?, ?, ?, ?, 'APPROVED', ?, 'TEAM1', ?)
            """,
            (local_user["id"], "Local", "3001111111", "Pereira", "Centro", "Equipo 1", 0),
        )
        local_admin_id = cur.lastrowid
        conn.commit()
        conn.close()
        return platform_admin_id, local_admin_id

    def _seed_ally(self):
        ally_user = db.ensure_user(940003, "ally_fee")
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO allies (user_id, business_name, owner_name, address, city, barrio, phone, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'APPROVED')
            """,
            (ally_user["id"], "Aliado Fee", "Owner", "Cra 1", "Pereira", "Centro", "3120000001"),
        )
        ally_id = cur.lastrowid
        conn.commit()
        conn.close()
        return ally_id

    def _seed_courier(self):
        courier_telegram_id = 940004
        courier_user = db.ensure_user(courier_telegram_id, "courier_fee")
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO couriers (user_id, full_name, id_number, phone, city, barrio, status, code)
            VALUES (?, ?, ?, ?, ?, ?, 'APPROVED', ?)
            """,
            (courier_user["id"], "Courier Fee", "CC9400", "3110000001", "Pereira", "Centro", "R-9400"),
        )
        courier_id = cur.lastrowid
        conn.commit()
        conn.close()
        return courier_id, courier_telegram_id

    def _link_ally_to_local_admin(self, balance):
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO admin_allies (admin_id, ally_id, status, balance, created_at, updated_at)
            VALUES (?, ?, 'APPROVED', ?, datetime('now'), datetime('now'))
            """,
            (self.local_admin_id, self.ally_id, balance),
        )
        conn.commit()
        conn.close()

    def _link_courier_to_local_admin(self, balance):
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO admin_couriers (admin_id, courier_id, status, balance, created_at, updated_at)
            VALUES (?, ?, 'APPROVED', ?, datetime('now'), datetime('now'))
            """,
            (self.local_admin_id, self.courier_id, balance),
        )
        conn.commit()
        conn.close()

    def _create_order(self, status="PICKED_UP", ally_id=None, creator_admin_id=None):
        order_id = db.create_order(
            ally_id=ally_id,
            creator_admin_id=creator_admin_id,
            customer_name="Cliente",
            customer_phone="3000000000",
            customer_address="Calle 1",
            customer_city="Pereira",
            customer_barrio="Centro",
            total_fee=5000,
        )
        db.assign_order_to_courier(order_id, self.courier_id, self.local_admin_id)
        if status == "PICKED_UP":
            db.set_order_status(order_id, "PICKED_UP", "pickup_confirmed_at")
        elif status == "CANCELLED":
            db.cancel_order(order_id, "SYSTEM")
        elif status == "PUBLISHED":
            db.set_order_status(order_id, "PUBLISHED", "published_at")
        else:
            db.set_order_status(order_id, status)
        return order_id

    def _count_courier_fee_ledger(self, order_id):
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT COUNT(*), COALESCE(SUM(amount), 0)
            FROM ledger
            WHERE ref_type = 'ORDER' AND ref_id = ? AND from_type = 'COURIER' AND from_id = ?
            """,
            (order_id, self.courier_id),
        )
        count, total = cur.fetchone()
        conn.close()
        return count, total

    def _get_settlement_row(self, order_id):
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT admin_id, ally_id, courier_id, courier_fee_charged, settlement_status
            FROM order_accounting_settlements
            WHERE order_id = ?
            """,
            (order_id,),
        )
        row = cur.fetchone()
        conn.close()
        return row

    def _run_delivered(self, order_id):
        update = _DummyUpdate(self.courier_telegram_id)
        context = _DummyContext()
        with patch.object(order_delivery, "_cancel_arrival_jobs", return_value=None), \
             patch.object(order_delivery, "_cancel_delivery_reminder_jobs", return_value=None), \
             patch.object(order_delivery, "_notify_ally_delivered", return_value=None):
            order_delivery._handle_delivered(update, context, order_id)
        return update, context

    def test_successful_delivery_charges_courier_once(self):
        order_id = self._create_order(status="PICKED_UP", ally_id=self.ally_id)

        update, _ = self._run_delivered(order_id)

        order = db.get_order_by_id(order_id)
        self.assertEqual("DELIVERED", order["status"])
        self.assertEqual(700, db.get_courier_link_balance(self.courier_id, self.local_admin_id))
        fee_count, fee_total = self._count_courier_fee_ledger(order_id)
        self.assertEqual(2, fee_count)
        self.assertEqual(300, fee_total)
        settlement = self._get_settlement_row(order_id)
        self.assertIsNotNone(settlement)
        self.assertEqual(self.local_admin_id, settlement["admin_id"])
        self.assertEqual(300, settlement["courier_fee_charged"])
        self.assertIn("Se descontaron $300", update.callback_query.messages[-1])

    def test_delivery_retry_does_not_duplicate_courier_charge(self):
        order_id = self._create_order(status="PICKED_UP", ally_id=self.ally_id)

        self._run_delivered(order_id)
        update, _ = self._run_delivered(order_id)

        self.assertEqual(700, db.get_courier_link_balance(self.courier_id, self.local_admin_id))
        fee_count, fee_total = self._count_courier_fee_ledger(order_id)
        self.assertEqual(2, fee_count)
        self.assertEqual(300, fee_total)
        self.assertIn("no esta en estado de entrega", update.callback_query.messages[-1].lower())

    def test_cancelled_or_expired_orders_do_not_trigger_delivery_courier_fee(self):
        cancelled_order_id = self._create_order(status="CANCELLED", ally_id=self.ally_id)
        update, _ = self._run_delivered(cancelled_order_id)
        cancelled_count, cancelled_total = self._count_courier_fee_ledger(cancelled_order_id)
        self.assertEqual(0, cancelled_count)
        self.assertEqual(0, cancelled_total)
        self.assertIn("no esta en estado de entrega", update.callback_query.messages[-1].lower())

        expired_order_id = self._create_order(status="PUBLISHED", ally_id=self.ally_id)
        context = _DummyContext()
        cycle_info = {"ally_id": self.ally_id, "admin_id": self.local_admin_id}
        with patch.object(order_delivery, "_cancel_no_response_job", return_value=None), \
             patch.object(order_delivery, "_cancel_order_expire_job", return_value=None), \
             patch.object(order_delivery, "_cancel_offer_jobs", return_value=None):
            order_delivery._expire_order(expired_order_id, cycle_info, context)

        expired_count, expired_total = self._count_courier_fee_ledger(expired_order_id)
        self.assertEqual(0, expired_count)
        self.assertEqual(0, expired_total)

    def test_admin_created_order_charges_only_courier_when_delivered(self):
        order_id = self._create_order(
            status="PICKED_UP",
            ally_id=None,
            creator_admin_id=self.local_admin_id,
        )

        self._run_delivered(order_id)

        fee_count, fee_total = self._count_courier_fee_ledger(order_id)
        self.assertEqual(2, fee_count)
        self.assertEqual(300, fee_total)
        settlement = self._get_settlement_row(order_id)
        self.assertIsNotNone(settlement)
        self.assertEqual(self.local_admin_id, settlement["admin_id"])
        self.assertEqual(300, settlement["courier_fee_charged"])

        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT COUNT(*)
            FROM ledger
            WHERE ref_type = 'ORDER' AND ref_id = ? AND from_type = 'ALLY'
            """,
            (order_id,),
        )
        ally_fee_count = cur.fetchone()[0]
        conn.close()
        self.assertEqual(0, ally_fee_count)


if __name__ == "__main__":
    unittest.main()
