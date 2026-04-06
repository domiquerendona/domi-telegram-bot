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
        self.assertEqual({"order_id": 99, "market_retry_count": 0}, args[4])

    @patch("order_delivery._cancel_offer_jobs")
    @patch("order_delivery.cancel_order")
    @patch("order_delivery.publish_order_to_couriers")
    @patch("order_delivery._notify_order_market_retry")
    @patch("order_delivery.delete_offer_queue")
    @patch("order_delivery.get_current_offer_for_order")
    @patch("order_delivery._cancel_offer_retry_job")
    @patch("order_delivery._cancel_order_expire_job")
    @patch("order_delivery._cancel_no_response_job")
    @patch("order_delivery.get_order_by_id")
    def test_expire_order_reintenta_mercado_antes_de_cancelar(
        self,
        mock_get_order_by_id,
        _mock_cancel_no_response_job,
        _mock_cancel_order_expire_job,
        _mock_cancel_offer_retry_job,
        mock_get_current_offer,
        _mock_delete_offer_queue,
        mock_notify_order_market_retry,
        mock_publish_order_to_couriers,
        mock_cancel_order,
        _mock_cancel_offer_jobs,
    ):
        mock_get_order_by_id.return_value = {
            "status": "PUBLISHED",
            "ally_id": 12,
            "creator_admin_id": None,
        }
        mock_get_current_offer.return_value = None
        context = self._context()
        context.bot_data = {"offer_cycles": {99: {}}, "offer_messages": {99: {}}}

        order_delivery._expire_order(
            99,
            {"ally_id": 12, "admin_id": 7, "market_retry_count": 0},
            context,
        )

        mock_cancel_order.assert_not_called()
        mock_publish_order_to_couriers.assert_called_once_with(
            order_id=99,
            ally_id=12,
            context=context,
            admin_id_override=None,
            skip_fee_check=True,
            reset_expire_window=True,
            market_retry_count=1,
            schedule_no_response=False,
        )
        mock_notify_order_market_retry.assert_called_once_with(context, mock_get_order_by_id.return_value, 1, 3)

    @patch("order_delivery.get_user_by_id")
    @patch("order_delivery.get_ally_by_id")
    @patch("order_delivery.publish_order_to_couriers")
    @patch("order_delivery._cancel_offer_jobs")
    @patch("order_delivery.cancel_order")
    @patch("order_delivery.delete_offer_queue")
    @patch("order_delivery.get_current_offer_for_order")
    @patch("order_delivery._cancel_offer_retry_job")
    @patch("order_delivery._cancel_order_expire_job")
    @patch("order_delivery._cancel_no_response_job")
    @patch("order_delivery.get_order_by_id")
    def test_expire_order_cancela_al_agotar_reintentos(
        self,
        mock_get_order_by_id,
        _mock_cancel_no_response_job,
        _mock_cancel_order_expire_job,
        _mock_cancel_offer_retry_job,
        mock_get_current_offer,
        _mock_delete_offer_queue,
        mock_cancel_order,
        _mock_cancel_offer_jobs,
        mock_publish_order_to_couriers,
        mock_get_ally_by_id,
        mock_get_user_by_id,
    ):
        mock_get_order_by_id.return_value = {
            "status": "PUBLISHED",
            "ally_id": 12,
            "creator_admin_id": None,
        }
        mock_get_current_offer.return_value = None
        mock_get_ally_by_id.return_value = {"user_id": 44}
        mock_get_user_by_id.return_value = {"telegram_id": 555}
        context = self._context()

        order_delivery._expire_order(
            99,
            {
                "ally_id": 12,
                "admin_id": 7,
                "market_retry_count": order_delivery.MARKET_RETRY_LIMIT,
            },
            context,
        )

        mock_publish_order_to_couriers.assert_not_called()
        mock_cancel_order.assert_called_once_with(99, "SYSTEM")
        context.bot.send_message.assert_called_once()
        self.assertIn(
            "despues de 3 reintentos del mercado",
            context.bot.send_message.call_args.kwargs["text"],
        )

    @patch("order_delivery._cancel_route_offer_jobs")
    @patch("order_delivery.cancel_route")
    @patch("order_delivery.publish_route_to_couriers")
    @patch("order_delivery._notify_route_market_retry")
    @patch("order_delivery.delete_route_offer_queue")
    @patch("order_delivery.get_current_route_offer")
    @patch("order_delivery._cancel_route_expire_job")
    @patch("order_delivery._cancel_route_offer_retry_job")
    @patch("order_delivery._cancel_route_no_response_job")
    @patch("order_delivery.get_route_by_id")
    def test_expire_route_reintenta_mercado_antes_de_cancelar(
        self,
        mock_get_route_by_id,
        _mock_cancel_route_no_response_job,
        _mock_cancel_route_offer_retry_job,
        _mock_cancel_route_expire_job,
        mock_get_current_route_offer,
        _mock_delete_route_offer_queue,
        mock_notify_route_market_retry,
        mock_publish_route_to_couriers,
        mock_cancel_route,
        _mock_cancel_route_offer_jobs,
    ):
        mock_get_route_by_id.return_value = {
            "status": "PUBLISHED",
            "ally_id": 21,
            "ally_admin_id_snapshot": 8,
        }
        mock_get_current_route_offer.return_value = None
        context = self._context()
        context.bot_data = {"route_offer_cycles": {77: {}}, "route_offer_messages": {77: {}}}

        order_delivery._expire_route(
            77,
            {"ally_id": 21, "admin_id": 8, "market_retry_count": 0},
            context,
        )

        mock_cancel_route.assert_not_called()
        mock_publish_route_to_couriers.assert_called_once_with(
            route_id=77,
            ally_id=21,
            context=context,
            admin_id_override=8,
            market_retry_count=1,
            schedule_no_response=False,
        )
        mock_notify_route_market_retry.assert_called_once_with(context, mock_get_route_by_id.return_value, 1, 3)

    @patch("order_delivery._schedule_persistent_job")
    @patch("order_delivery.get_route_by_id")
    @patch("order_delivery._cancel_route_expire_job")
    def test_schedule_route_expire_job_persiste_retry_count(
        self,
        _mock_cancel_route_expire_job,
        mock_get_route_by_id,
        mock_schedule_persistent_job,
    ):
        mock_get_route_by_id.return_value = {"status": "PUBLISHED", "published_at": None}
        context = self._context()

        order_delivery._schedule_route_expire_job(
            context,
            route_id=77,
            market_retry_count=2,
        )

        mock_schedule_persistent_job.assert_called_once()
        args = mock_schedule_persistent_job.call_args[0]
        self.assertIs(args[0], context)
        self.assertIs(args[1], order_delivery._route_expire_job)
        self.assertEqual(order_delivery.ROUTE_MAX_CYCLE_SECONDS, args[2])
        self.assertEqual("route_expire_77", args[3])
        self.assertEqual({"route_id": 77, "market_retry_count": 2}, args[4])

    @patch("order_delivery.get_pending_scheduled_jobs")
    @patch("order_delivery.get_current_route_offer")
    @patch("order_delivery.get_current_offer_for_order")
    @patch("order_delivery.get_routes_by_status")
    @patch("order_delivery.get_all_orders")
    @patch("order_delivery.get_order_excluded_couriers")
    def test_recover_active_offer_dispatches_recupera_market_retry_count(
        self,
        mock_get_order_excluded_couriers,
        mock_get_all_orders,
        mock_get_routes_by_status,
        mock_get_current_offer_for_order,
        mock_get_current_route_offer,
        mock_get_pending_scheduled_jobs,
    ):
        mock_get_order_excluded_couriers.return_value = set()
        mock_get_all_orders.return_value = [
            {"id": 11, "status": "PUBLISHED", "created_at": "2026-04-04 10:00:00"},
        ]
        mock_get_routes_by_status.return_value = [
            {
                "id": 22,
                "status": "PUBLISHED",
                "published_at": "2026-04-04 10:05:00",
                "ally_id": 5,
                "ally_admin_id_snapshot": 8,
            },
        ]
        mock_get_current_offer_for_order.return_value = {"queue_id": 501, "offered_at": "2026-04-04 10:09:00"}
        mock_get_current_route_offer.return_value = {"queue_id": 601, "offered_at": "2026-04-04 10:09:30"}
        mock_get_pending_scheduled_jobs.return_value = [
            {
                "job_name": "order_expire_11",
                "job_data": "{\"order_id\": 11, \"market_retry_count\": 2}",
            },
            {
                "job_name": "route_expire_22",
                "job_data": "{\"route_id\": 22, \"market_retry_count\": 1}",
            },
        ]

        updater = SimpleNamespace(
            bot=MagicMock(),
            job_queue=MagicMock(),
            dispatcher=SimpleNamespace(bot_data={}),
        )
        updater.job_queue.get_jobs_by_name.return_value = []

        order_delivery.recover_active_offer_dispatches(updater)

        self.assertEqual(2, updater.dispatcher.bot_data["offer_cycles"][11]["market_retry_count"])
        self.assertEqual(1, updater.dispatcher.bot_data["route_offer_cycles"][22]["market_retry_count"])

        run_once_calls = updater.job_queue.run_once.call_args_list
        order_call = next(call for call in run_once_calls if call.kwargs["name"] == "offer_timeout_11_501")
        route_call = next(call for call in run_once_calls if call.kwargs["name"] == "route_offer_timeout_22_601")
        self.assertEqual(2, order_call.kwargs["context"]["market_retry_count"])
        self.assertEqual(1, route_call.kwargs["context"]["market_retry_count"])

    @patch("order_delivery.get_user_by_id")
    @patch("order_delivery.get_ally_by_id")
    @patch("order_delivery.publish_route_to_couriers")
    @patch("order_delivery._cancel_route_offer_jobs")
    @patch("order_delivery.cancel_route")
    @patch("order_delivery.delete_route_offer_queue")
    @patch("order_delivery.get_current_route_offer")
    @patch("order_delivery._cancel_route_expire_job")
    @patch("order_delivery._cancel_route_offer_retry_job")
    @patch("order_delivery._cancel_route_no_response_job")
    @patch("order_delivery.get_route_by_id")
    def test_expire_route_cancela_al_agotar_reintentos(
        self,
        mock_get_route_by_id,
        _mock_cancel_route_no_response_job,
        _mock_cancel_route_offer_retry_job,
        _mock_cancel_route_expire_job,
        mock_get_current_route_offer,
        _mock_delete_route_offer_queue,
        mock_cancel_route,
        _mock_cancel_route_offer_jobs,
        mock_publish_route_to_couriers,
        mock_get_ally_by_id,
        mock_get_user_by_id,
    ):
        mock_get_route_by_id.return_value = {
            "status": "PUBLISHED",
            "ally_id": 21,
            "ally_admin_id_snapshot": 8,
        }
        mock_get_current_route_offer.return_value = None
        mock_get_ally_by_id.return_value = {"user_id": 71}
        mock_get_user_by_id.return_value = {"telegram_id": 999}
        context = self._context()

        order_delivery._expire_route(
            77,
            {"ally_id": 21, "admin_id": 8, "market_retry_count": order_delivery.MARKET_RETRY_LIMIT},
            context,
        )

        mock_publish_route_to_couriers.assert_not_called()
        mock_cancel_route.assert_called_once_with(77, "SYSTEM")
        context.bot.send_message.assert_called_once()
        self.assertIn(
            "despues de 3 reintentos del mercado",
            context.bot.send_message.call_args.kwargs["text"],
        )

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


class SupportRequestAdminRoutingTests(unittest.TestCase):
    def _update(self, telegram_id=7001):
        query = MagicMock()
        return SimpleNamespace(
            callback_query=query,
            effective_user=SimpleNamespace(id=telegram_id),
        )

    def _context(self):
        return SimpleNamespace(bot=MagicMock(), job_queue=MagicMock(), bot_data={})

    @patch("order_delivery._notify_admin_pin_issue")
    @patch("order_delivery._schedule_support_follow_up_jobs")
    @patch("order_delivery.create_or_get_pending_support_request", return_value=(501, True))
    @patch("order_delivery._is_courier_gps_active", return_value=True)
    @patch("order_delivery.get_courier_by_telegram_id")
    @patch("order_delivery.get_order_by_id")
    @patch("order_delivery.get_approved_admin_id_for_courier")
    def test_order_delivery_pin_issue_uses_order_snapshot_admin(
        self,
        mock_get_approved_admin_id_for_courier,
        mock_get_order_by_id,
        mock_get_courier_by_telegram_id,
        _mock_is_courier_gps_active,
        mock_create_or_get_pending_support_request,
        _mock_schedule_support_follow_up_jobs,
        mock_notify_admin_pin_issue,
    ):
        mock_get_order_by_id.return_value = {
            "id": 91,
            "status": "PICKED_UP",
            "courier_id": 44,
            "courier_admin_id_snapshot": 11,
        }
        mock_get_courier_by_telegram_id.return_value = {"id": 44}
        mock_notify_admin_pin_issue.return_value = True

        order_delivery._handle_pin_issue_report(self._update(), self._context(), 91)

        mock_create_or_get_pending_support_request.assert_called_once_with(
            courier_id=44,
            admin_id=11,
            order_id=91,
            support_type=order_delivery.SUPPORT_TYPE_DELIVERY_PIN,
        )
        mock_get_approved_admin_id_for_courier.assert_not_called()

    @patch("order_delivery._notify_admin_route_pin_issue")
    @patch("order_delivery._schedule_support_follow_up_jobs")
    @patch("order_delivery.create_or_get_pending_support_request", return_value=(601, True))
    @patch("order_delivery.get_route_destinations")
    @patch("order_delivery._is_courier_gps_active", return_value=True)
    @patch("order_delivery.get_courier_by_telegram_id")
    @patch("order_delivery.get_route_by_id")
    @patch("order_delivery.get_approved_admin_id_for_courier")
    def test_route_stop_pin_issue_uses_route_snapshot_admin(
        self,
        mock_get_approved_admin_id_for_courier,
        mock_get_route_by_id,
        mock_get_courier_by_telegram_id,
        _mock_is_courier_gps_active,
        mock_get_route_destinations,
        mock_create_or_get_pending_support_request,
        _mock_schedule_support_follow_up_jobs,
        mock_notify_admin_route_pin_issue,
    ):
        mock_get_route_by_id.return_value = {
            "id": 73,
            "status": "ACCEPTED",
            "courier_id": 44,
            "courier_admin_id_snapshot": 12,
        }
        mock_get_courier_by_telegram_id.return_value = {"id": 44}
        mock_get_route_destinations.return_value = [{"sequence": 2}]
        mock_notify_admin_route_pin_issue.return_value = True

        order_delivery._handle_route_pin_issue(self._update(), self._context(), 73, 2)

        mock_create_or_get_pending_support_request.assert_called_once_with(
            courier_id=44,
            admin_id=12,
            route_id=73,
            route_seq=2,
            support_type=order_delivery.SUPPORT_TYPE_ROUTE_STOP_PIN,
        )
        mock_get_approved_admin_id_for_courier.assert_not_called()

    @patch("order_delivery._notify_admin_pickup_pinissue")
    @patch("order_delivery._schedule_support_follow_up_jobs")
    @patch("order_delivery.create_or_get_pending_support_request", return_value=(701, True))
    @patch("order_delivery.get_courier_by_telegram_id")
    @patch("order_delivery.get_order_by_id")
    @patch("order_delivery.get_approved_admin_id_for_courier")
    def test_order_pickup_pin_issue_uses_order_snapshot_admin(
        self,
        mock_get_approved_admin_id_for_courier,
        mock_get_order_by_id,
        mock_get_courier_by_telegram_id,
        mock_create_or_get_pending_support_request,
        _mock_schedule_support_follow_up_jobs,
        mock_notify_admin_pickup_pinissue,
    ):
        mock_get_order_by_id.return_value = {
            "id": 55,
            "status": "ACCEPTED",
            "courier_id": 44,
            "courier_admin_id_snapshot": 13,
        }
        mock_get_courier_by_telegram_id.return_value = {"id": 44}
        mock_notify_admin_pickup_pinissue.return_value = True

        order_delivery._handle_order_pickup_pinissue(self._update(), self._context(), 55)

        mock_create_or_get_pending_support_request.assert_called_once_with(
            courier_id=44,
            admin_id=13,
            order_id=55,
            support_type=order_delivery.SUPPORT_TYPE_PICKUP_PIN,
        )
        mock_get_approved_admin_id_for_courier.assert_not_called()

    @patch("order_delivery._notify_admin_route_pickup_pinissue")
    @patch("order_delivery._schedule_support_follow_up_jobs")
    @patch("order_delivery.create_or_get_pending_support_request", return_value=(801, True))
    @patch("order_delivery.get_courier_by_telegram_id")
    @patch("order_delivery.get_route_by_id")
    @patch("order_delivery.get_approved_admin_id_for_courier")
    def test_route_pickup_pin_issue_uses_route_snapshot_admin(
        self,
        mock_get_approved_admin_id_for_courier,
        mock_get_route_by_id,
        mock_get_courier_by_telegram_id,
        mock_create_or_get_pending_support_request,
        _mock_schedule_support_follow_up_jobs,
        mock_notify_admin_route_pickup_pinissue,
    ):
        mock_get_route_by_id.return_value = {
            "id": 66,
            "status": "ACCEPTED",
            "courier_id": 44,
            "courier_admin_id_snapshot": 14,
        }
        mock_get_courier_by_telegram_id.return_value = {"id": 44}
        mock_notify_admin_route_pickup_pinissue.return_value = True

        order_delivery._handle_route_pickup_pinissue(self._update(), self._context(), 66)

        mock_create_or_get_pending_support_request.assert_called_once_with(
            courier_id=44,
            admin_id=14,
            route_id=66,
            route_seq=0,
            support_type=order_delivery.SUPPORT_TYPE_ROUTE_PICKUP_PIN,
        )
        mock_get_approved_admin_id_for_courier.assert_not_called()

    @patch("order_delivery._notify_admin_pickup_pinissue", return_value=False)
    @patch("order_delivery._schedule_support_follow_up_jobs")
    @patch("order_delivery.create_or_get_pending_support_request", return_value=(701, True))
    @patch("order_delivery.get_courier_by_telegram_id")
    @patch("order_delivery.get_order_by_id")
    def test_order_pickup_pin_issue_reports_retry_when_notification_fails(
        self,
        mock_get_order_by_id,
        mock_get_courier_by_telegram_id,
        _mock_create_or_get_pending_support_request,
        _mock_schedule_support_follow_up_jobs,
        _mock_notify_admin_pickup_pinissue,
    ):
        mock_get_order_by_id.return_value = {
            "id": 55,
            "status": "ACCEPTED",
            "courier_id": 44,
            "courier_admin_id_snapshot": 13,
        }
        mock_get_courier_by_telegram_id.return_value = {"id": 44}
        update = self._update()

        order_delivery._handle_order_pickup_pinissue(update, self._context(), 55)

        self.assertIn(
            "La solicitud quedo registrada",
            update.callback_query.edit_message_text.call_args.args[0],
        )

    @patch("order_delivery.get_pending_support_request", return_value=None)
    @patch("order_delivery.get_order_by_id")
    def test_admin_pickup_pinissue_action_filters_pending_support_by_pickup_type(
        self,
        mock_get_order_by_id,
        mock_get_pending_support_request,
    ):
        mock_get_order_by_id.return_value = {
            "id": 55,
            "status": "ACCEPTED",
        }
        update = self._update()

        order_delivery._handle_admin_pickup_pinissue_action(update, self._context(), 55, 701, "confirm")

        mock_get_pending_support_request.assert_called_once_with(
            order_id=55,
            support_type=order_delivery.SUPPORT_TYPE_PICKUP_PIN,
        )
        self.assertIn(
            "Esta solicitud ya fue resuelta",
            update.callback_query.edit_message_text.call_args.args[0],
        )

    @patch("order_delivery.get_pending_support_request", return_value=None)
    @patch("order_delivery.get_order_by_id")
    def test_admin_delivery_pinissue_action_filters_pending_support_by_delivery_type(
        self,
        mock_get_order_by_id,
        mock_get_pending_support_request,
    ):
        mock_get_order_by_id.return_value = {
            "id": 91,
            "status": "PICKED_UP",
        }
        update = self._update()

        order_delivery._handle_admin_pinissue_action(update, self._context(), 91, "fin")

        mock_get_pending_support_request.assert_called_once_with(
            order_id=91,
            support_type=order_delivery.SUPPORT_TYPE_DELIVERY_PIN,
        )
        self.assertIn(
            "No hay solicitud de ayuda pendiente",
            update.callback_query.edit_message_text.call_args.args[0],
        )

    @patch("order_delivery.get_pending_support_request", return_value=None)
    @patch("order_delivery.get_route_by_id")
    def test_admin_route_pickup_pinissue_action_filters_pending_support_by_route_pickup_type(
        self,
        mock_get_route_by_id,
        mock_get_pending_support_request,
    ):
        mock_get_route_by_id.return_value = {
            "id": 66,
            "status": "ACCEPTED",
        }
        update = self._update()

        order_delivery._handle_admin_route_pickup_pinissue_action(update, self._context(), 66, 801, "confirm")

        mock_get_pending_support_request.assert_called_once_with(
            route_id=66,
            route_seq=0,
            support_type=order_delivery.SUPPORT_TYPE_ROUTE_PICKUP_PIN,
        )
        self.assertIn(
            "Esta solicitud ya fue resuelta",
            update.callback_query.edit_message_text.call_args.args[0],
        )

    @patch("order_delivery.get_pending_support_request", return_value=None)
    @patch("order_delivery.get_route_by_id")
    def test_admin_route_delivery_pinissue_action_filters_pending_support_by_route_stop_type(
        self,
        mock_get_route_by_id,
        mock_get_pending_support_request,
    ):
        mock_get_route_by_id.return_value = {
            "id": 73,
            "status": "ACCEPTED",
        }
        update = self._update()

        order_delivery._handle_admin_route_pinissue_action(update, self._context(), 73, 2, "fin")

        mock_get_pending_support_request.assert_called_once_with(
            route_id=73,
            route_seq=2,
            support_type=order_delivery.SUPPORT_TYPE_ROUTE_STOP_PIN,
        )
        self.assertIn(
            "No hay solicitud de ayuda pendiente",
            update.callback_query.edit_message_text.call_args.args[0],
        )

    @patch("order_delivery._get_pickup_address", return_value="Bodega Central")
    @patch("order_delivery._get_pickup_coords", return_value=(4.81, -75.69))
    @patch("order_delivery.get_user_by_id")
    @patch("order_delivery.get_admin_by_id")
    def test_notify_admin_pickup_pinissue_uses_pickup_helper_when_order_has_no_pickup_address(
        self,
        mock_get_admin_by_id,
        mock_get_user_by_id,
        _mock_get_pickup_coords,
        mock_get_pickup_address,
    ):
        mock_get_admin_by_id.return_value = {"user_id": 101}

        def _user_side_effect(user_id):
            if user_id == 101:
                return {"telegram_id": 9001}
            return None

        mock_get_user_by_id.side_effect = _user_side_effect
        context = self._context()
        order = {
            "id": 55,
            "accepted_at": "2026-04-01 10:00:00",
            "ally_id": None,
            "creator_admin_id": None,
        }
        courier = {
            "user_id": 202,
            "full_name": "Courier Uno",
            "phone": "3110000001",
            "live_lat": 4.80,
            "live_lng": -75.68,
        }

        notified = order_delivery._notify_admin_pickup_pinissue(context, order, courier, 13, 701)

        self.assertTrue(notified)
        mock_get_pickup_address.assert_called_once_with(order)
        context.bot.send_message.assert_called_once()
        self.assertIn(
            "Punto de recogida: Bodega Central",
            context.bot.send_message.call_args.kwargs["text"],
        )

    @patch("order_delivery._dispatch_support_request_notification", return_value=True)
    @patch("order_delivery._schedule_support_follow_up_jobs")
    @patch("order_delivery.create_or_get_pending_support_request", return_value=(701, False))
    @patch("order_delivery.get_courier_by_telegram_id")
    @patch("order_delivery.get_order_by_id")
    def test_order_pickup_pin_issue_duplicate_retries_notification(
        self,
        mock_get_order_by_id,
        mock_get_courier_by_telegram_id,
        _mock_create_or_get_pending_support_request,
        mock_schedule_support_follow_up_jobs,
        mock_dispatch_support_request_notification,
    ):
        mock_get_order_by_id.return_value = {
            "id": 55,
            "status": "ACCEPTED",
            "courier_id": 44,
            "courier_admin_id_snapshot": 13,
        }
        mock_get_courier_by_telegram_id.return_value = {"id": 44}
        update = self._update()
        context = self._context()

        order_delivery._handle_order_pickup_pinissue(update, context, 55)

        mock_schedule_support_follow_up_jobs.assert_called_once_with(context, 701)
        mock_dispatch_support_request_notification.assert_called_once_with(context, 701, 13)
        self.assertIn(
            "Reenviamos la alerta a tu administrador",
            update.callback_query.edit_message_text.call_args.args[0],
        )

    @patch("order_delivery._dispatch_support_request_notification", return_value=False)
    @patch("order_delivery._schedule_support_follow_up_jobs")
    @patch("order_delivery.create_or_get_pending_support_request", return_value=(701, False))
    @patch("order_delivery.get_courier_by_telegram_id")
    @patch("order_delivery.get_order_by_id")
    def test_order_pickup_pin_issue_duplicate_reports_retry_when_redispatch_fails(
        self,
        mock_get_order_by_id,
        mock_get_courier_by_telegram_id,
        _mock_create_or_get_pending_support_request,
        mock_schedule_support_follow_up_jobs,
        mock_dispatch_support_request_notification,
    ):
        mock_get_order_by_id.return_value = {
            "id": 55,
            "status": "ACCEPTED",
            "courier_id": 44,
            "courier_admin_id_snapshot": 13,
        }
        mock_get_courier_by_telegram_id.return_value = {"id": 44}
        update = self._update()
        context = self._context()

        order_delivery._handle_order_pickup_pinissue(update, context, 55)

        mock_schedule_support_follow_up_jobs.assert_called_once_with(context, 701)
        mock_dispatch_support_request_notification.assert_called_once_with(context, 701, 13)
        self.assertIn(
            "La solicitud para este pedido ya estaba registrada",
            update.callback_query.edit_message_text.call_args.args[0],
        )

    @patch("order_delivery.get_approved_admin_id_for_courier", return_value=99)
    def test_resolve_support_admin_id_falls_back_to_current_admin_when_no_snapshot(
        self,
        mock_get_approved_admin_id_for_courier,
    ):
        admin_id = order_delivery._resolve_support_admin_id(44, None)

        self.assertEqual(99, admin_id)
        mock_get_approved_admin_id_for_courier.assert_called_once_with(44)


if __name__ == "__main__":
    unittest.main()
