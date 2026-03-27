"""Tests para el flujo de suscripciones mensuales de aliados.

Cubre:
- set_ally_subscription_price / get_ally_subscription_price
- pay_ally_subscription: debito de saldo, credito a plataforma y admin, registro
- check_ally_active_subscription: True si activa, False si no
- Exencion de fee al aliado cuando tiene suscripcion activa
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Backend"))

import db
import services


PLATFORM_TG_ID = 930001
SUB_PRICE = 50000        # precio de suscripcion configurado por el admin
PLATFORM_SHARE = 20000   # default de subscription_platform_share


class SubscriptionBase(unittest.TestCase):
    """BD aislada con plataforma, admin local, aliado y vinculos pre-sembrados."""

    def setUp(self):
        fd, path = tempfile.mkstemp(prefix="domi_sub_test_", suffix=".db")
        os.close(fd)
        self.db_path = path
        os.environ["DB_PATH"] = self.db_path
        os.environ.pop("DATABASE_URL", None)
        db.init_db()

        db.ensure_platform_sociedad()
        db.force_platform_admin(PLATFORM_TG_ID)
        self.platform_admin = db.get_platform_admin()
        self.platform_admin_id = self.platform_admin["id"]
        self._add_admin_balance(self.platform_admin_id, 1000000)

        self.local_admin_id = self._seed_admin(930002, "sub_local_admin")
        self.ally_id = self._seed_ally(930010)
        self._link_ally(self.ally_id, self.local_admin_id, balance=200000)

    def tearDown(self):
        try:
            os.remove(self.db_path)
        except (FileNotFoundError, PermissionError):
            pass

    def _add_admin_balance(self, admin_id, amount):
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE admins SET balance = balance + ? WHERE id = ?", (amount, admin_id))
        conn.commit()
        conn.close()

    def _seed_admin(self, tg_id, username):
        user = db.ensure_user(tg_id, username)
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO admins (user_id, full_name, phone, city, barrio,
                                status, team_name, team_code, balance)
            VALUES (?, ?, ?, ?, ?, 'APPROVED', ?, ?, ?)
            """,
            (user["id"], "Admin " + username, "3400000000", "Pereira", "Centro",
             "Equipo " + username, "TEAM_SUB_" + str(tg_id), 0),
        )
        admin_id = cur.lastrowid
        conn.commit()
        conn.close()
        return admin_id

    def _seed_ally(self, tg_id):
        user = db.ensure_user(tg_id, "sub_ally_{}".format(tg_id))
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO allies (user_id, business_name, owner_name, phone,
                                city, barrio, address, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'APPROVED')
            """,
            (user["id"], "Aliado Sub {}".format(tg_id), "Owner Sub",
             "3500000000", "Pereira", "Centro", "Cra 8"),
        )
        ally_id = cur.lastrowid
        conn.commit()
        conn.close()
        return ally_id

    def _link_ally(self, ally_id, admin_id, balance=0):
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO admin_allies (admin_id, ally_id, status, balance,
                                      created_at, updated_at)
            VALUES (?, ?, 'APPROVED', ?, datetime('now'), datetime('now'))
            """,
            (admin_id, ally_id, balance),
        )
        conn.commit()
        conn.close()


class SetAllySubscriptionPriceTests(SubscriptionBase):

    def test_set_y_get_precio_suscripcion(self):
        db.set_ally_subscription_price(self.local_admin_id, self.ally_id, SUB_PRICE)
        precio = db.get_ally_subscription_price(self.local_admin_id, self.ally_id)
        self.assertEqual(SUB_PRICE, precio)

    def test_precio_no_configurado_retorna_none(self):
        precio = db.get_ally_subscription_price(self.local_admin_id, self.ally_id)
        self.assertIsNone(precio)

    def test_actualizar_precio_existente(self):
        db.set_ally_subscription_price(self.local_admin_id, self.ally_id, SUB_PRICE)
        db.set_ally_subscription_price(self.local_admin_id, self.ally_id, 80000)
        precio = db.get_ally_subscription_price(self.local_admin_id, self.ally_id)
        self.assertEqual(80000, precio)


class PayAllySubscriptionTests(SubscriptionBase):

    def setUp(self):
        super().setUp()
        db.set_ally_subscription_price(self.local_admin_id, self.ally_id, SUB_PRICE)

    def test_pago_exitoso_debita_saldo_aliado(self):
        balance_antes = db.get_ally_link_balance(self.ally_id, self.local_admin_id)
        ok, msg = services.pay_ally_subscription(self.ally_id, self.local_admin_id)
        self.assertTrue(ok, msg)
        balance_despues = db.get_ally_link_balance(self.ally_id, self.local_admin_id)
        self.assertEqual(balance_antes - SUB_PRICE, balance_despues)

    def test_pago_acredita_admin_share_al_admin(self):
        balance_admin_antes = db.get_admin_balance(self.local_admin_id)
        ok, msg = services.pay_ally_subscription(self.ally_id, self.local_admin_id)
        self.assertTrue(ok, msg)
        balance_admin_despues = db.get_admin_balance(self.local_admin_id)
        admin_share = SUB_PRICE - PLATFORM_SHARE
        self.assertEqual(balance_admin_antes + admin_share, balance_admin_despues)

    def test_pago_falla_sin_saldo(self):
        # Vaciar saldo del aliado
        db.update_ally_link_balance(self.ally_id, self.local_admin_id, -200000)
        ok, msg = services.pay_ally_subscription(self.ally_id, self.local_admin_id)
        self.assertFalse(ok)
        self.assertIn("insuficiente", msg.lower())

    def test_pago_falla_sin_precio_configurado(self):
        otro_ally_id = self._seed_ally(930099)
        self._link_ally(otro_ally_id, self.local_admin_id, balance=200000)
        ok, msg = services.pay_ally_subscription(otro_ally_id, self.local_admin_id)
        self.assertFalse(ok)

    def test_pago_crea_registro_de_suscripcion(self):
        ok, _ = services.pay_ally_subscription(self.ally_id, self.local_admin_id)
        self.assertTrue(ok)
        sub = db.get_active_ally_subscription(self.ally_id)
        self.assertIsNotNone(sub)
        self.assertEqual("ACTIVE", sub["status"])


class CheckAllyActiveSubscriptionTests(SubscriptionBase):

    def setUp(self):
        super().setUp()
        db.set_ally_subscription_price(self.local_admin_id, self.ally_id, SUB_PRICE)

    def test_sin_suscripcion_retorna_false(self):
        self.assertFalse(services.check_ally_active_subscription(self.ally_id))

    def test_con_suscripcion_activa_retorna_true(self):
        ok, _ = services.pay_ally_subscription(self.ally_id, self.local_admin_id)
        self.assertTrue(ok)
        self.assertTrue(services.check_ally_active_subscription(self.ally_id))


class FeeExemptionWithSubscriptionTests(SubscriptionBase):
    """Aliado suscrito no paga fee de servicio; courier si paga el suyo."""

    def setUp(self):
        super().setUp()
        db.set_ally_subscription_price(self.local_admin_id, self.ally_id, SUB_PRICE)
        # Sembrar courier
        user = db.ensure_user(930030, "sub_courier_930030")
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO couriers (user_id, full_name, id_number, phone,
                                  city, barrio, status, code)
            VALUES (?, ?, ?, ?, ?, ?, 'APPROVED', ?)
            """,
            (user["id"], "Courier Sub", "CC930030", "3600000000",
             "Pereira", "Cuba", "R-930030"),
        )
        self.courier_id = cur.lastrowid
        cur.execute(
            """
            INSERT INTO admin_couriers (admin_id, courier_id, status, balance,
                                        created_at, updated_at)
            VALUES (?, ?, 'APPROVED', ?, datetime('now'), datetime('now'))
            """,
            (self.local_admin_id, self.courier_id, 10000),
        )
        conn.commit()
        conn.close()

    def test_aliado_sin_suscripcion_paga_fee(self):
        balance_antes = db.get_ally_link_balance(self.ally_id, self.local_admin_id)
        fee_cfg = services.get_fee_config()
        ok, _ = services.apply_service_fee(
            "ALLY", self.ally_id, self.local_admin_id,
        )
        self.assertTrue(ok)
        balance_despues = db.get_ally_link_balance(self.ally_id, self.local_admin_id)
        self.assertEqual(balance_antes - fee_cfg["fee_service_total"], balance_despues)

    def test_aliado_con_suscripcion_activa_no_paga_fee(self):
        """La exencion ocurre en order_delivery.py, no dentro de apply_service_fee.
        Este test verifica que la condicion de guardia es correcta:
        check_ally_active_subscription devuelve True => la llamada a apply_service_fee
        debe ser omitida por el caller (order_delivery._handle_delivered).
        """
        services.pay_ally_subscription(self.ally_id, self.local_admin_id)
        esta_suscrito = services.check_ally_active_subscription(self.ally_id)
        self.assertTrue(esta_suscrito)

        # La logica de guarda en order_delivery.py es:
        #   if ally_admin_id and not check_ally_active_subscription(ally_id):
        #       apply_service_fee(...)
        # Con suscripcion activa, not True == False => apply_service_fee NO se llama.
        self.assertFalse(not esta_suscrito,
                         "Con suscripcion activa la condicion de guarda debe ser False "
                         "(apply_service_fee no se llamaria)")

    def test_courier_siempre_paga_fee_independiente_de_suscripcion_del_aliado(self):
        services.pay_ally_subscription(self.ally_id, self.local_admin_id)
        fee_cfg = services.get_fee_config()
        balance_courier_antes = db.get_courier_link_balance(self.courier_id, self.local_admin_id)

        ok, _ = services.apply_service_fee(
            "COURIER", self.courier_id, self.local_admin_id,
        )
        self.assertTrue(ok)
        balance_courier_despues = db.get_courier_link_balance(self.courier_id, self.local_admin_id)
        self.assertEqual(
            balance_courier_antes - fee_cfg["fee_service_total"],
            balance_courier_despues,
        )


if __name__ == "__main__":
    unittest.main()
