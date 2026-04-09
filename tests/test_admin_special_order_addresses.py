import ast
import re
import unittest
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[1]
ORDER_HANDLER_PATH = REPO_ROOT / "Backend" / "handlers" / "order.py"


class _InlineKeyboardButton:
    def __init__(self, text, callback_data=None):
        self.text = text
        self.callback_data = callback_data


class _InlineKeyboardMarkup:
    def __init__(self, keyboard):
        self.inline_keyboard = keyboard


class _DummyMessage:
    def __init__(self, text="", location=None):
        self.text = text
        self.location = location
        self.reply_calls = []

    def reply_text(self, text, reply_markup=None):
        self.reply_calls.append({"text": text, "reply_markup": reply_markup})


class _DummyQuery:
    def __init__(self, data=""):
        self.data = data
        self.answer_calls = 0
        self.edit_calls = []
        self.message = _DummyMessage()

    def answer(self):
        self.answer_calls += 1

    def edit_message_text(self, text, reply_markup=None):
        self.edit_calls.append({"text": text, "reply_markup": reply_markup})


def _extract_namespace():
    tree = ast.parse(ORDER_HANDLER_PATH.read_text(encoding="utf-8"))
    target_functions = {
        "_pedido_is_system_address",
        "_pedido_visible_address_text",
        "_pedido_pickup_option_text",
        "_pedido_customer_address_button_text",
        "_pedido_reply_text",
        "_pedido_merge_instruction_text",
        "_pedido_prompt_notes_or_continue",
        "_pedido_start_pickup_fix",
        "_pedido_human_label",
        "_pedido_requires_human_detail",
        "_admin_pedido_render_preview",
        "_admin_pedido_render_pickup_save_prompt",
        "_admin_pedido_prompt_pickup_detail",
        "_admin_pedido_prompt_delivery_detail",
        "_resolve_admin_for_special_order",
        "admin_nuevo_pedido_start",
        "mostrar_pregunta_base",
        "_admin_pedido_pedir_instruc",
        "admin_pedido_pickup_callback",
        "admin_pedido_geo_pickup_callback",
        "admin_pedido_pickup_detalle_handler",
        "admin_pedido_addr_selected",
        "admin_pedido_geo_callback",
        "admin_pedido_cust_addr_detalle_handler",
        "admin_pedido_instruc_handler",
        "pedido_geo_ubicacion_callback",
        "pedido_direccion_cliente",
        "pedido_seleccionar_direccion_callback",
        "pedido_pickup_callback",
        "pedido_pickup_geo_callback",
        "pedido_pickup_nueva_detalles_handler",
    }

    selected_nodes = []
    found = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in target_functions:
            selected_nodes.append(node)
            found.add(node.name)

    missing = target_functions - found
    if missing:
        raise AssertionError(
            "No se pudieron extraer nodos esperados de order.py: {}".format(sorted(missing))
        )

    namespace = {
        "re": re,
        "InlineKeyboardButton": _InlineKeyboardButton,
        "InlineKeyboardMarkup": _InlineKeyboardMarkup,
        "ADMIN_PEDIDO_PICKUP": 908,
        "ADMIN_PEDIDO_CUST_ADDR": 911,
        "ADMIN_PEDIDO_INSTRUC": 913,
        "ADMIN_PEDIDO_SEL_CUST_ADDR": 918,
        "ADMIN_PEDIDO_SAVE_PICKUP": 919,
        "ADMIN_PEDIDO_PICKUP_DETALLE": 1024,
        "ADMIN_PEDIDO_CUST_ADDR_DETALLE": 1025,
        "ADMIN_PEDIDO_COMISION": 1011,
        "PEDIDO_UBICACION": 8,
        "PEDIDO_DIRECCION": 9,
        "PEDIDO_SELECCIONAR_DIRECCION": 10,
        "PEDIDO_INSTRUCCIONES_EXTRA": 11,
        "PEDIDO_REQUIERE_BASE": 12,
        "PEDIDO_PICKUP_SELECTOR": 12,
        "PEDIDO_PICKUP_NUEVA_UBICACION": 13,
        "PEDIDO_PICKUP_NUEVA_DETALLES": 14,
        "PEDIDO_PICKUP_NUEVA_CIUDAD": 15,
        "PEDIDO_PICKUP_NUEVA_BARRIO": 16,
        "PEDIDO_PICKUP_GUARDAR": 17,
        "MIN_ADMIN_OPERATING_BALANCE": 2000,
        "PARKING_FEE_AMOUNT": 1200,
        "logger": SimpleNamespace(info=lambda *args, **kwargs: None, warning=lambda *args, **kwargs: None),
        "_admin_ped_preview_text": lambda user_data: ("PREVIEW", None),
        "_admin_pedido_mostrar_selector_cliente": lambda update, context, edit=False: 917,
        "_admin_pedido_calcular_preview": lambda update, context, edit=False: 912,
        "mostrar_selector_pickup": lambda update, context, edit=False: 12,
        "mostrar_resumen_confirmacion": lambda update, context, edit=False: 18,
        "mostrar_resumen_confirmacion_msg": lambda update, context: 18,
        "continuar_despues_pickup": lambda update, context, edit=False: 19,
        "_maybe_cache_confirmed_geo": lambda context: None,
        "_geo_siguiente_o_gps": lambda query, context, yes, no, state: state,
        "save_confirmed_geocoding": lambda text, lat, lng: None,
        "resolve_location_next": lambda text, seen, city_hint=None: None,
        "_order_city_hint": lambda context: None,
        "_mostrar_confirmacion_geocode": lambda *args, **kwargs: None,
        "get_fee_config": lambda: {"fee_service_total": 2500, "fee_platform_share": 2500},
        "get_admin_location_by_id": lambda loc_id, admin_id: None,
        "get_admin_customer_address_by_id": lambda address_id, customer_id=None: None,
        "get_default_ally_location": lambda ally_id: None,
        "get_customer_address_by_id": lambda address_id, customer_id=None: None,
        "get_ally_parking_fee_enabled": lambda ally_id: False,
        "get_admin_by_telegram_id": lambda telegram_id: None,
        "user_has_platform_admin": lambda telegram_id: False,
        "get_user_by_telegram_id": lambda telegram_id: None,
        "get_platform_admin": lambda: None,
        "get_admin_by_id": lambda admin_id: None,
        "get_admin_balance": lambda admin_id: 0,
        "get_sociedad_balance": lambda: 0,
        "get_admin_locations": lambda admin_id: [],
        "list_order_templates": lambda admin_id: [],
        "show_flow_menu": lambda update, context, text: None,
        "has_valid_coords": lambda lat, lng: lat is not None and lng is not None,
        "update_ally_location": lambda location_id, address, city, barrio, phone=None: True,
        "update_admin_location": lambda **kwargs: True,
        "update_customer_address": lambda **kwargs: True,
        "update_admin_customer_address": lambda **kwargs: True,
        "increment_customer_address_usage": lambda address_id, customer_id: None,
        "increment_admin_customer_address_usage": lambda address_id, customer_id: None,
        "increment_setting_counter": lambda *args, **kwargs: None,
        "ConversationHandler": SimpleNamespace(END=-1),
    }
    def _resolve_owned_admin_actor(
        telegram_id,
        selected_admin_id=None,
        prefer_platform=False,
        legacy_counter_key=None,
        invalid_counter_key=None,
    ):
        if selected_admin_id is not None:
            selected_admin = namespace["get_admin_by_id"](selected_admin_id)
            user = namespace["get_user_by_telegram_id"](telegram_id)
            if not selected_admin or not user:
                return None
            if int(selected_admin.get("user_id") or 0) != int(user.get("id") or 0):
                return None
            return selected_admin
        fallback_admin = namespace["get_admin_by_telegram_id"](telegram_id)
        if not prefer_platform or not namespace["user_has_platform_admin"](telegram_id):
            return fallback_admin
        platform_admin = namespace["get_platform_admin"]()
        if not platform_admin:
            return fallback_admin
        return namespace["get_admin_by_id"](platform_admin["id"]) or fallback_admin

    namespace["resolve_owned_admin_actor"] = _resolve_owned_admin_actor
    compiled = compile(
        ast.Module(body=selected_nodes, type_ignores=[]),
        filename=str(ORDER_HANDLER_PATH),
        mode="exec",
    )
    exec(compiled, namespace)
    return namespace


class AdminSpecialOrderAddressTests(unittest.TestCase):
    def test_special_order_prefers_explicit_platform_admin_for_same_user(self):
        namespace = _extract_namespace()
        namespace["get_admin_by_telegram_id"] = lambda telegram_id: {
            "id": 8,
            "user_id": 55,
            "status": "APPROVED",
            "team_code": "LOCAL",
            "balance": 0,
        }
        namespace["user_has_platform_admin"] = lambda telegram_id: True
        namespace["get_user_by_telegram_id"] = lambda telegram_id: {"id": 55}
        namespace["get_platform_admin"] = lambda: {"id": 2}
        namespace["get_admin_by_id"] = lambda admin_id: {
            "id": admin_id,
            "user_id": 55,
            "status": "APPROVED",
            "team_code": "PLATFORM",
            "balance": 973800,
        }

        admin = namespace["_resolve_admin_for_special_order"](573102188155, selected_admin_id=2)

        self.assertEqual(2, admin["id"])
        self.assertEqual("PLATFORM", admin["team_code"])

    def test_special_order_insufficient_platform_balance_offers_sociedad_with_cta(self):
        namespace = _extract_namespace()
        namespace["get_admin_by_telegram_id"] = lambda telegram_id: {
            "id": 2,
            "user_id": 55,
            "status": "APPROVED",
            "team_code": "PLATFORM",
        }
        namespace["get_user_by_telegram_id"] = lambda telegram_id: {"id": 55}
        namespace["get_admin_by_id"] = lambda admin_id: {
            "id": admin_id,
            "user_id": 55,
            "status": "APPROVED",
            "team_code": "PLATFORM",
        }
        namespace["get_admin_balance"] = lambda admin_id: 0
        namespace["get_sociedad_balance"] = lambda: 999600

        query = _DummyQuery("admin_nuevo_pedido_2")
        update = SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=573102188155))
        context = SimpleNamespace(user_data={})

        state = namespace["admin_nuevo_pedido_start"](update, context)

        self.assertEqual(-1, state)
        self.assertIn("Tu saldo personal actual: $0", query.edit_calls[-1]["text"])
        self.assertIn("Saldo Sociedad disponible: $999,600", query.edit_calls[-1]["text"])
        buttons = query.edit_calls[-1]["reply_markup"].inline_keyboard
        self.assertEqual("admin_sociedad_retiro_2", buttons[0][0].callback_data)

    def test_special_order_rejects_selected_admin_from_other_user(self):
        namespace = _extract_namespace()
        namespace["get_admin_by_telegram_id"] = lambda telegram_id: {
            "id": 8,
            "user_id": 55,
            "status": "APPROVED",
            "team_code": "LOCAL",
        }
        namespace["get_user_by_telegram_id"] = lambda telegram_id: {"id": 55}
        namespace["get_admin_by_id"] = lambda admin_id: {
            "id": admin_id,
            "user_id": 999,
            "status": "APPROVED",
            "team_code": "LOCAL",
        }

        query = _DummyQuery("admin_nuevo_pedido_77")
        update = SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=573102188155))
        context = SimpleNamespace(user_data={})

        state = namespace["admin_nuevo_pedido_start"](update, context)

        self.assertEqual(-1, state)
        self.assertIn("No se pudo validar el administrador", query.edit_calls[-1]["text"])

    def test_system_address_helper_detects_gps_coords_and_urls(self):
        namespace = _extract_namespace()

        is_system = namespace["_pedido_is_system_address"]
        visible = namespace["_pedido_visible_address_text"]

        self.assertTrue(is_system(""))
        self.assertTrue(is_system("GPS (4.80692, -75.68057)"))
        self.assertTrue(is_system("4.80692, -75.68057"))
        self.assertTrue(is_system("https://maps.google.com/?q=4.80692,-75.68057"))
        self.assertFalse(is_system("Calle 12 # 3-45, Barrio Cuba"))
        self.assertEqual(
            "Ubicacion pendiente de detallar",
            visible("GPS (4.80692, -75.68057)"),
        )

    def test_saved_pickup_with_system_text_prompts_for_human_detail(self):
        namespace = _extract_namespace()
        namespace["get_admin_location_by_id"] = lambda loc_id, admin_id: {
            "id": loc_id,
            "label": "Principal",
            "address": "GPS (4.80692, -75.68057)",
            "city": "Pereira",
            "barrio": "Centro",
            "phone": None,
            "lat": 4.80692,
            "lng": -75.68057,
        }

        query = _DummyQuery("admin_pedido_pickup_7")
        update = SimpleNamespace(callback_query=query)
        context = SimpleNamespace(user_data={"admin_ped_admin_id": 11})

        state = namespace["admin_pedido_pickup_callback"](update, context)

        self.assertEqual(1024, state)
        self.assertEqual(1, query.answer_calls)
        self.assertIn("solo con coordenadas", query.edit_calls[-1]["text"])
        self.assertEqual(7, context.user_data["admin_ped_geo_pickup_pending"]["location_id"])

    def test_pickup_detail_handler_repairs_saved_admin_location(self):
        namespace = _extract_namespace()
        update_calls = []
        namespace["update_admin_location"] = lambda **kwargs: update_calls.append(kwargs) or True
        namespace["_admin_pedido_mostrar_selector_cliente"] = (
            lambda update, context, edit=False: 917
        )

        update = SimpleNamespace(message=_DummyMessage("Calle 18 # 22-30, Barrio Cuba"))
        context = SimpleNamespace(
            user_data={
                "admin_ped_admin_id": 11,
                "admin_ped_geo_pickup_pending": {
                    "location_id": 7,
                    "label": "GPS (4.80692, -75.68057)",
                    "address": "GPS (4.80692, -75.68057)",
                    "city": "Pereira",
                    "barrio": "Cuba",
                    "phone": "3000000000",
                    "lat": 4.80692,
                    "lng": -75.68057,
                },
            }
        )

        state = namespace["admin_pedido_pickup_detalle_handler"](update, context)

        self.assertEqual(917, state)
        self.assertEqual("Calle 18 # 22-30, Barrio Cuba", context.user_data["admin_ped_pickup_addr"])
        self.assertEqual(7, context.user_data["admin_ped_pickup_id"])
        self.assertEqual("Calle 18 # 22-30, Barrio Cuba", update_calls[0]["address"])
        self.assertEqual("Calle 18 # 22-30, Barrio Cuba", update_calls[0]["label"])
        self.assertNotIn("admin_ped_geo_pickup_pending", context.user_data)

    def test_saved_customer_address_with_system_text_prompts_for_human_detail(self):
        namespace = _extract_namespace()
        namespace["get_admin_customer_address_by_id"] = lambda address_id, customer_id=None: {
            "id": address_id,
            "customer_id": 44,
            "label": "Principal",
            "address_text": "GPS (4.80692, -75.68057)",
            "city": "Pereira",
            "barrio": "Centro",
            "notes": "Porteria azul",
            "lat": 4.80692,
            "lng": -75.68057,
        }

        query = _DummyQuery("acust_pedido_addr_9")
        update = SimpleNamespace(callback_query=query)
        context = SimpleNamespace(
            user_data={"admin_ped_admin_id": 11, "admin_ped_cust_name": "Daniela"}
        )

        state = namespace["admin_pedido_addr_selected"](update, context)

        self.assertEqual(1025, state)
        self.assertIn("solo con coordenadas", query.edit_calls[-1]["text"])
        self.assertEqual(9, context.user_data["admin_ped_geo_cust_pending"]["address_id"])
        self.assertEqual(44, context.user_data["admin_ped_geo_cust_pending"]["customer_id"])

    def test_customer_detail_handler_repairs_saved_admin_customer_address(self):
        namespace = _extract_namespace()
        update_calls = []
        usage_calls = []
        namespace["update_admin_customer_address"] = (
            lambda **kwargs: update_calls.append(kwargs) or True
        )
        namespace["increment_admin_customer_address_usage"] = (
            lambda address_id, customer_id: usage_calls.append((address_id, customer_id))
        )
        update = SimpleNamespace(message=_DummyMessage("Conjunto Los Pinos Torre 2"))
        context = SimpleNamespace(
            user_data={
                "admin_ped_admin_id": 11,
                "admin_ped_geo_cust_pending": {
                    "address_id": 9,
                    "customer_id": 44,
                    "label": "Principal",
                    "notes": "Porteria azul",
                    "parking_status": "ALLY_YES",
                    "city": "Pereira",
                    "barrio": "Cuba",
                    "lat": 4.80692,
                    "lng": -75.68057,
                }
            }
        )

        state = namespace["admin_pedido_cust_addr_detalle_handler"](update, context)

        self.assertEqual(12, state)
        self.assertEqual("Conjunto Los Pinos Torre 2", context.user_data["admin_ped_cust_addr"])
        self.assertEqual(1200, context.user_data["admin_ped_parking_fee"])
        self.assertEqual("Conjunto Los Pinos Torre 2", update_calls[0]["address_text"])
        self.assertEqual([(9, 44)], usage_calls)
        self.assertNotIn("admin_ped_geo_cust_pending", context.user_data)
        self.assertIn("BASE REQUERIDA", update.message.reply_calls[-1]["text"])

    def test_pickup_geo_confirmation_requires_human_detail_before_save(self):
        namespace = _extract_namespace()

        query = _DummyQuery("admin_pedido_geo_pickup_si")
        update = SimpleNamespace(callback_query=query)
        context = SimpleNamespace(
            user_data={
                "admin_ped_geo_pickup_pending": {
                    "address": "GPS (4.80692, -75.68057)",
                    "lat": 4.80692,
                    "lng": -75.68057,
                    "city": "",
                    "barrio": "",
                    "source": "gps",
                },
                "pending_geo_lat": 4.80692,
                "pending_geo_lng": -75.68057,
                "pending_geo_text": "",
                "pending_geo_seen": ["4.80692,-75.68057"],
            }
        )

        state = namespace["admin_pedido_geo_pickup_callback"](update, context)

        self.assertEqual(1024, state)
        self.assertIn("direccion visible exacta de recogida", query.edit_calls[-1]["text"])
        self.assertNotIn("admin_ped_pickup_addr", context.user_data)

    def test_pickup_text_confirmation_uses_written_address_without_extra_prompt(self):
        namespace = _extract_namespace()

        query = _DummyQuery("admin_pedido_geo_pickup_si")
        update = SimpleNamespace(callback_query=query)
        context = SimpleNamespace(
            user_data={
                "admin_ped_geo_pickup_pending": {
                    "address": "Carrera 7 # 12-34, Pereira, Risaralda, Colombia",
                    "lat": 4.80692,
                    "lng": -75.68057,
                    "city": "Pereira",
                    "barrio": "Centro",
                    "original_text": "Carrera 7 # 12-34, Local 2",
                    "source": "geocode",
                },
                "pending_geo_lat": 4.80692,
                "pending_geo_lng": -75.68057,
                "pending_geo_text": "Carrera 7 # 12-34, Local 2",
                "pending_geo_seen": ["pid-1"],
            }
        )

        state = namespace["admin_pedido_geo_pickup_callback"](update, context)

        self.assertEqual(919, state)
        self.assertEqual("Carrera 7 # 12-34, Local 2", context.user_data["admin_ped_pickup_addr"])
        self.assertIn("Guardar esta direccion en Mis Dirs", query.edit_calls[-1]["text"])

    def test_delivery_geo_confirmation_requires_human_detail_before_preview(self):
        namespace = _extract_namespace()

        query = _DummyQuery("admin_pedido_geo_si")
        update = SimpleNamespace(callback_query=query)
        context = SimpleNamespace(
            user_data={
                "admin_ped_geo_cust_pending": {
                    "address": "GPS (4.80692, -75.68057)",
                    "lat": 4.80692,
                    "lng": -75.68057,
                    "city": "",
                    "barrio": "",
                    "source": "gps",
                },
                "pending_geo_lat": 4.80692,
                "pending_geo_lng": -75.68057,
                "pending_geo_text": "",
                "pending_geo_seen": ["4.80692,-75.68057"],
            }
        )

        state = namespace["admin_pedido_geo_callback"](update, context)

        self.assertEqual(1025, state)
        self.assertIn("direccion visible exacta de entrega", query.edit_calls[-1]["text"])
        self.assertNotIn("admin_ped_cust_addr", context.user_data)

    def test_delivery_text_confirmation_uses_written_address_without_extra_prompt(self):
        namespace = _extract_namespace()

        query = _DummyQuery("admin_pedido_geo_si")
        update = SimpleNamespace(callback_query=query)
        context = SimpleNamespace(
            user_data={
                "admin_ped_geo_cust_pending": {
                    "address": "Calle 21 # 8-40, Pereira, Risaralda, Colombia",
                    "lat": 4.80692,
                    "lng": -75.68057,
                    "city": "Pereira",
                    "barrio": "Centro",
                    "original_text": "Calle 21 # 8-40 apto 301",
                    "source": "geocode",
                },
                "pending_geo_lat": 4.80692,
                "pending_geo_lng": -75.68057,
                "pending_geo_text": "Calle 21 # 8-40 apto 301",
                "pending_geo_seen": ["pid-2"],
            }
        )

        state = namespace["admin_pedido_geo_callback"](update, context)

        self.assertEqual(12, state)
        self.assertEqual("Calle 21 # 8-40 apto 301", context.user_data["admin_ped_cust_addr"])
        self.assertIn("BASE REQUERIDA", query.edit_calls[-1]["text"])

    def test_pickup_detail_from_preview_returns_to_preview(self):
        namespace = _extract_namespace()
        namespace["_admin_ped_preview_text"] = lambda user_data: ("PREVIEW FINAL", None)

        update = SimpleNamespace(message=_DummyMessage("Bodega Calle 8 # 10-20"))
        context = SimpleNamespace(
            user_data={
                "admin_ped_edit_from_preview": True,
                "admin_ped_geo_pickup_pending": {
                    "address": "GPS (4.80692, -75.68057)",
                    "lat": 4.80692,
                    "lng": -75.68057,
                    "city": "Pereira",
                    "barrio": "Centro",
                },
            }
        )

        state = namespace["admin_pedido_pickup_detalle_handler"](update, context)

        self.assertEqual(913, state)
        self.assertNotIn("admin_ped_edit_from_preview", context.user_data)
        self.assertEqual("PREVIEW FINAL", update.message.reply_calls[-1]["text"])

    def test_admin_instruction_handler_merges_saved_note_with_extra_text(self):
        namespace = _extract_namespace()
        update = SimpleNamespace(message=_DummyMessage("Llamar al llegar"))
        context = SimpleNamespace(user_data={"admin_ped_addr_notes": "Porteria azul"})

        state = namespace["admin_pedido_instruc_handler"](update, context)

        self.assertEqual(913, state)
        self.assertEqual(
            "Porteria azul\nLlamar al llegar",
            context.user_data["admin_ped_instruc"],
        )


class AllyOrderAddressUnificationTests(unittest.TestCase):
    def test_ally_delivery_text_confirmation_uses_written_address_without_extra_prompt(self):
        namespace = _extract_namespace()

        query = _DummyQuery("pedido_geo_si")
        update = SimpleNamespace(callback_query=query)
        context = SimpleNamespace(
            user_data={
                "pedido_pending_location_source": "geocode",
                "pedido_pending_customer_city": "Pereira",
                "pedido_pending_customer_barrio": "Centro",
                "pending_geo_lat": 4.80692,
                "pending_geo_lng": -75.68057,
                "pending_geo_text": "Calle 21 # 8-40 apto 301",
                "pending_geo_seen": ["pid-ally-1"],
            }
        )

        state = namespace["pedido_geo_ubicacion_callback"](update, context)

        self.assertEqual(12, state)
        self.assertEqual("Calle 21 # 8-40 apto 301", context.user_data["customer_address"])
        self.assertEqual("Pereira", context.user_data["customer_city"])
        self.assertIn("Se usara esta direccion", query.edit_calls[-1]["text"])

    def test_ally_recent_system_address_requires_human_detail(self):
        namespace = _extract_namespace()

        query = _DummyQuery("pedido_geo_si")
        update = SimpleNamespace(callback_query=query)
        context = SimpleNamespace(
            user_data={
                "pedido_pending_location_source": "recent_address",
                "pedido_pending_prefill_address": "GPS (4.80692, -75.68057)",
                "pedido_pending_customer_city": "Pereira",
                "pedido_pending_customer_barrio": "Centro",
                "pending_geo_lat": 4.80692,
                "pending_geo_lng": -75.68057,
                "pending_geo_text": "",
                "pending_geo_seen": ["pid-ally-2"],
            }
        )

        state = namespace["pedido_geo_ubicacion_callback"](update, context)

        self.assertEqual(9, state)
        self.assertIn("solo con coordenadas", query.edit_calls[-1]["text"])

    def test_ally_saved_customer_address_with_system_text_prompts_repair(self):
        namespace = _extract_namespace()
        namespace["get_customer_address_by_id"] = lambda address_id, customer_id=None: {
            "id": address_id,
            "label": "Casa",
            "address_text": "GPS (4.80692, -75.68057)",
            "city": "Pereira",
            "barrio": "Centro",
            "notes": "Porteria azul",
            "lat": 4.80692,
            "lng": -75.68057,
            "parking_status": "ALLY_YES",
        }
        namespace["get_ally_parking_fee_enabled"] = lambda ally_id: True

        query = _DummyQuery("pedido_sel_addr_5")
        update = SimpleNamespace(callback_query=query)
        context = SimpleNamespace(user_data={"customer_id": 44, "ally_id": 77})

        state = namespace["pedido_seleccionar_direccion_callback"](update, context)

        self.assertEqual(9, state)
        self.assertEqual(5, context.user_data["pedido_pending_address_fix"]["address_id"])
        self.assertIn("solo con coordenadas", query.edit_calls[-1]["text"])

    def test_ally_customer_detail_repair_updates_saved_address(self):
        namespace = _extract_namespace()
        update_calls = []
        usage_calls = []
        namespace["update_customer_address"] = lambda **kwargs: update_calls.append(kwargs) or True
        namespace["increment_customer_address_usage"] = (
            lambda address_id, customer_id: usage_calls.append((address_id, customer_id))
        )
        namespace["mostrar_selector_pickup"] = lambda update, context, edit=False: 12

        update = SimpleNamespace(message=_DummyMessage("Conjunto Los Pinos Torre 2"))
        context = SimpleNamespace(
            user_data={
                "pedido_pending_address_fix": {
                    "address_id": 9,
                    "customer_id": 44,
                    "label": "Casa",
                    "notes": "",
                    "parking_status": "ALLY_YES",
                    "city": "Pereira",
                    "barrio": "Cuba",
                    "lat": 4.80692,
                    "lng": -75.68057,
                }
            }
        )

        state = namespace["pedido_direccion_cliente"](update, context)

        self.assertEqual(12, state)
        self.assertEqual("Conjunto Los Pinos Torre 2", context.user_data["customer_address"])
        self.assertEqual("Conjunto Los Pinos Torre 2", update_calls[0]["address_text"])
        self.assertEqual([(9, 44)], usage_calls)

    def test_ally_pickup_text_confirmation_uses_written_address_without_extra_prompt(self):
        namespace = _extract_namespace()

        query = _DummyQuery("pickup_geo_si")
        update = SimpleNamespace(callback_query=query)
        context = SimpleNamespace(
            user_data={
                "pedido_pending_pickup_resolution": {
                    "source": "geocode",
                    "original_text": "Bodega Calle 8 # 10-20",
                    "city": "Pereira",
                    "barrio": "Centro",
                },
                "pending_geo_lat": 4.80692,
                "pending_geo_lng": -75.68057,
                "pending_geo_text": "Bodega Calle 8 # 10-20",
                "pending_geo_seen": ["pickup-1"],
            }
        )

        state = namespace["pedido_pickup_geo_callback"](update, context)

        self.assertEqual(15, state)
        self.assertEqual("Bodega Calle 8 # 10-20", context.user_data["new_pickup_address"])
        self.assertIn("Ciudad de la recogida", query.edit_calls[-1]["text"])

    def test_ally_saved_pickup_with_system_text_prompts_repair(self):
        namespace = _extract_namespace()
        namespace["get_default_ally_location"] = lambda ally_id: {
            "id": 7,
            "label": "Base",
            "address": "GPS (4.80692, -75.68057)",
            "city": "Pereira",
            "barrio": "Cuba",
            "phone": "3000000000",
            "lat": 4.80692,
            "lng": -75.68057,
        }

        query = _DummyQuery("pickup_select_base")
        update = SimpleNamespace(callback_query=query)
        context = SimpleNamespace(user_data={"ally": {"id": 11}})

        state = namespace["pedido_pickup_callback"](update, context)

        self.assertEqual(14, state)
        self.assertEqual(7, context.user_data["pedido_pending_pickup_fix"]["location_id"])
        self.assertIn("solo con coordenadas", query.edit_calls[-1]["text"])

    def test_ally_pickup_repair_updates_saved_location(self):
        namespace = _extract_namespace()
        update_calls = []
        namespace["update_ally_location"] = (
            lambda location_id, address, city, barrio, phone=None: update_calls.append(
                (location_id, address, city, barrio, phone)
            )
            or True
        )
        namespace["continuar_despues_pickup"] = lambda update, context, edit=False: 19

        update = SimpleNamespace(message=_DummyMessage("Bodega Calle 8 # 10-20"))
        context = SimpleNamespace(
            user_data={
                "pedido_pending_pickup_fix": {
                    "location_id": 7,
                    "city": "Pereira",
                    "barrio": "Cuba",
                    "phone": "3000000000",
                    "lat": 4.80692,
                    "lng": -75.68057,
                }
            }
        )

        state = namespace["pedido_pickup_nueva_detalles_handler"](update, context)

        self.assertEqual(19, state)
        self.assertEqual(
            (7, "Bodega Calle 8 # 10-20", "Pereira", "Cuba", "3000000000"),
            update_calls[0],
        )
        self.assertEqual("Bodega Calle 8 # 10-20", context.user_data["pickup_address"])


if __name__ == "__main__":
    unittest.main()
