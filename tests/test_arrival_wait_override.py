import os
import sys
import unittest
import types
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Backend"))

telegram_stub = types.ModuleType("telegram")


class _InlineKeyboardButton:
    def __init__(self, text, callback_data=None):
        self.text = text
        self.callback_data = callback_data


class _InlineKeyboardMarkup:
    def __init__(self, inline_keyboard):
        self.inline_keyboard = inline_keyboard


telegram_stub.InlineKeyboardButton = _InlineKeyboardButton
telegram_stub.InlineKeyboardMarkup = _InlineKeyboardMarkup
sys.modules.setdefault("telegram", telegram_stub)

import order_delivery


class ArrivalWaitOverrideTests(unittest.TestCase):
    def _context(self, job_context=None):
        return SimpleNamespace(
            bot=MagicMock(),
            job_queue=MagicMock(),
            bot_data={},
            job=SimpleNamespace(context=job_context or {}, name="test_job"),
        )

    @patch("order_delivery.mark_job_executed")
    @patch("order_delivery._release_order_by_timeout")
    @patch("order_delivery.get_order_by_id")
    def test_order_deadline_job_no_libera_si_espera_manual_esta_activa(
        self,
        mock_get_order_by_id,
        mock_release_order_by_timeout,
        _mock_mark_job_executed,
    ):
        mock_get_order_by_id.return_value = {
            "status": "ACCEPTED",
            "courier_arrived_at": None,
            "arrival_wait_override": 1,
            "arrival_wait_override_at": "2026-04-01 10:00:00",
            "courier_id": 77,
        }

        order_delivery._arrival_deadline_job(self._context({"order_id": 123}))

        mock_release_order_by_timeout.assert_not_called()

    @patch("order_delivery.mark_job_executed")
    @patch("order_delivery._release_route_by_timeout")
    @patch("order_delivery.get_route_by_id")
    def test_route_deadline_job_no_libera_si_espera_manual_esta_activa(
        self,
        mock_get_route_by_id,
        mock_release_route_by_timeout,
        _mock_mark_job_executed,
    ):
        mock_get_route_by_id.return_value = {
            "status": "ACCEPTED",
            "arrival_wait_override": 1,
            "arrival_wait_override_at": "2026-04-01 10:05:00",
        }

        order_delivery._route_arrival_deadline_job(
            self._context({"route_id": 456, "courier_id": 88})
        )

        mock_release_route_by_timeout.assert_not_called()

    @patch("order_delivery._schedule_persistent_job")
    @patch("order_delivery.get_order_by_id")
    @patch("order_delivery._cancel_order_expire_job")
    def test_schedule_order_expire_job_reinicia_ventana_en_reoferta(
        self,
        _mock_cancel_order_expire_job,
        mock_get_order_by_id,
        mock_schedule_persistent_job,
    ):
        mock_get_order_by_id.return_value = {"status": "PUBLISHED"}
        context = self._context()

        order_delivery._schedule_order_expire_job(
            context,
            order_id=99,
            reset_window=True,
        )

        mock_schedule_persistent_job.assert_called_once()
        args = mock_schedule_persistent_job.call_args[0]
        self.assertIs(args[0], context)
        self.assertIs(args[1], order_delivery._order_expire_job)
        self.assertEqual(order_delivery.MAX_CYCLE_SECONDS, args[2])
        self.assertEqual("order_expire_99", args[3])
        self.assertEqual({"order_id": 99}, args[4])

    @patch("order_delivery.mark_job_executed")
    @patch("order_delivery.get_courier_by_id")
    @patch("order_delivery.get_user_by_id")
    @patch("order_delivery.get_ally_by_id")
    @patch("order_delivery.get_order_by_id")
    def test_order_wait_override_reminder_envia_recordatorio_suave(
        self,
        mock_get_order_by_id,
        mock_get_ally_by_id,
        mock_get_user_by_id,
        mock_get_courier_by_id,
        _mock_mark_job_executed,
    ):
        mock_get_order_by_id.return_value = {
            "status": "ACCEPTED",
            "arrival_wait_override": 1,
            "ally_id": 11,
            "courier_id": 22,
        }
        mock_get_ally_by_id.return_value = {"user_id": 101}
        mock_get_courier_by_id.return_value = {"user_id": 202}

        def _user_side_effect(user_id):
            if user_id == 101:
                return {"telegram_id": 9001}
            if user_id == 202:
                return {"telegram_id": 9002}
            return None

        mock_get_user_by_id.side_effect = _user_side_effect
        context = self._context({"order_id": 77})

        order_delivery._arrival_wait_override_reminder_job(context)

        context.bot.send_message.assert_called_once()
        kwargs = context.bot.send_message.call_args.kwargs
        self.assertEqual(9001, kwargs["chat_id"])
        self.assertIn("sigues en espera manual", kwargs["text"])
        self.assertIn("buscar otro repartidor", kwargs["text"].lower())

    @patch("order_delivery.get_route_destinations")
    @patch("order_delivery.get_active_routes_by_ally")
    @patch("order_delivery.get_active_orders_by_ally")
    @patch("order_delivery.get_ally_by_user_id")
    @patch("order_delivery.get_user_by_telegram_id")
    def test_ally_active_orders_muestra_indicador_de_espera_manual(
        self,
        mock_get_user_by_telegram_id,
        mock_get_ally_by_user_id,
        mock_get_active_orders_by_ally,
        mock_get_active_routes_by_ally,
        mock_get_route_destinations,
    ):
        mock_get_user_by_telegram_id.return_value = {"id": 1}
        mock_get_ally_by_user_id.return_value = {"id": 10}
        mock_get_active_orders_by_ally.return_value = [{
            "id": 501,
            "status": "ACCEPTED",
            "customer_name": "Ana",
            "customer_address": "Calle 1",
            "arrival_wait_override": 1,
        }]
        mock_get_active_routes_by_ally.return_value = [{
            "id": 701,
            "status": "ACCEPTED",
            "arrival_wait_override": 1,
        }]
        mock_get_route_destinations.return_value = [{"sequence": 1}, {"sequence": 2}]

        reply_text = MagicMock()
        update = SimpleNamespace(
            effective_user=SimpleNamespace(id=12345),
            message=SimpleNamespace(reply_text=reply_text),
        )
        context = SimpleNamespace()

        order_delivery.ally_active_orders(update, context)

        sent_texts = [
            call.args[0]
            for call in reply_text.call_args_list
            if call.args
        ]
        self.assertTrue(any("Ruta #701" in text and "Espera manual: activa" in text for text in sent_texts))
        self.assertTrue(any("Pedido #501" in text and "Espera manual: activa" in text for text in sent_texts))


if __name__ == "__main__":
    unittest.main()
