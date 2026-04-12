import ast
import ast
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


class _DummyBot:
    def __init__(self):
        self.messages = []

    def send_message(self, chat_id, text, reply_markup=None):
        self.messages.append(
            {"chat_id": chat_id, "text": text, "reply_markup": reply_markup}
        )


class _DummyMessage:
    def __init__(self, chat_id=940003):
        self.chat_id = chat_id


class _DummyQuery:
    def __init__(self):
        self.message = _DummyMessage()
        self.edit_calls = []
        self.reply_markup_calls = []

    def edit_message_text(self, text, reply_markup=None):
        self.edit_calls.append({"text": text, "reply_markup": reply_markup})

    def edit_message_reply_markup(self, reply_markup=None):
        self.reply_markup_calls.append(reply_markup)


def _extract_namespace():
    tree = ast.parse(ORDER_HANDLER_PATH.read_text(encoding="utf-8"))
    target_functions = {"_handle_post_order_ui"}

    selected_nodes = []
    found = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in target_functions:
            selected_nodes.append(node)
            found.add(node.name)

    missing = target_functions - found
    if missing:
        raise AssertionError(
            "No se pudieron extraer nodos esperados de order.py: {}".format(
                sorted(missing)
            )
        )

    namespace = {
        "InlineKeyboardButton": _InlineKeyboardButton,
        "InlineKeyboardMarkup": _InlineKeyboardMarkup,
        "PEDIDO_GUARDAR_CLIENTE": 41,
        "PEDIDO_GUARDAR_DIR_EXISTENTE": 42,
        "ConversationHandler": SimpleNamespace(END=-1),
        "construir_preview_oferta": lambda *args, **kwargs: "PREVIEW EXACTO DEL COURIER",
        "build_market_launch_status_text": lambda count: "Mercado: {}".format(count),
        "build_order_creation_summary_text": (
            lambda order, market_status_text: (
                "Pedido #{} creado exitosamente.\n\nValor del servicio: ${:,}\n\n{}".format(
                    order["id"],
                    int(order["total_fee"] or 0),
                    market_status_text,
                )
            )
        ),
        "get_order_by_id": lambda order_id: {"id": order_id, "total_fee": 9200},
        "get_preview_buttons": lambda: _InlineKeyboardMarkup(
            [[_InlineKeyboardButton("Preview", callback_data="preview_ok")]]
        ),
        "_append_success_followup": lambda success_text, followup_text: "{}\n\n{}".format(
            success_text,
            followup_text,
        ),
        "get_ally_customer_by_phone": lambda ally_id, phone: None,
        "has_valid_coords": lambda lat, lng: lat is not None and lng is not None,
        "find_matching_customer_address": lambda *args, **kwargs: None,
        "show_main_menu": lambda update, context, text=None: context.menu_calls.append(text),
    }

    compiled = compile(
        ast.Module(body=selected_nodes, type_ignores=[]),
        filename=str(ORDER_HANDLER_PATH),
        mode="exec",
    )
    exec(compiled, namespace)
    return namespace


class OrderCreationFollowupTests(unittest.TestCase):
    def test_new_customer_followup_keeps_visible_value(self):
        namespace = _extract_namespace()
        query = _DummyQuery()
        update = SimpleNamespace(callback_query=query)
        context = SimpleNamespace(
            user_data={
                "service_type": "Mensajeria",
                "requires_cash": False,
                "cash_required_amount": 0,
                "customer_address": "Calle 25 # 8-19",
                "customer_city": "Pereira",
                "customer_barrio": "Cuba",
                "customer_phone": "3137481811",
                "is_new_customer": True,
                "dropoff_lat": 4.80692,
                "dropoff_lng": -75.68057,
                "pickup_city": "Pereira",
                "pickup_barrio": "Centro",
            },
            bot=_DummyBot(),
            menu_calls=[],
        )

        state = namespace["_handle_post_order_ui"](
            query,
            update,
            context,
            order_id=901,
            ally_id=7,
            published_count=2,
            pricing={},
            pickup_text="Cra 10 # 20-30",
        )

        self.assertEqual(41, state)
        self.assertIn("Valor del servicio: $9,200", query.edit_calls[-1]["text"])
        self.assertIn("Quieres guardar este cliente", query.edit_calls[-1]["text"])
        self.assertEqual("PREVIEW EXACTO DEL COURIER", context.bot.messages[-1]["text"])
        self.assertEqual(
            "Pedido #901 creado exitosamente.\n\nValor del servicio: $9,200\n\nMercado: 2",
            context.user_data["pedido_success_text"],
        )

    def test_existing_customer_new_address_followup_keeps_visible_value(self):
        namespace = _extract_namespace()
        namespace["get_ally_customer_by_phone"] = lambda ally_id, phone: {
            "id": 44,
            "name": "Daniela",
        }
        query = _DummyQuery()
        update = SimpleNamespace(callback_query=query)
        context = SimpleNamespace(
            user_data={
                "service_type": "Mensajeria",
                "requires_cash": False,
                "cash_required_amount": 0,
                "customer_address": "Calle 25 # 8-19 apto 302",
                "customer_city": "Pereira",
                "customer_barrio": "Cuba",
                "customer_phone": "3137481811",
                "dropoff_lat": 4.80692,
                "dropoff_lng": -75.68057,
                "pickup_city": "Pereira",
                "pickup_barrio": "Centro",
            },
            bot=_DummyBot(),
            menu_calls=[],
        )

        state = namespace["_handle_post_order_ui"](
            query,
            update,
            context,
            order_id=901,
            ally_id=7,
            published_count=3,
            pricing={},
            pickup_text="Cra 10 # 20-30",
        )

        self.assertEqual(42, state)
        self.assertEqual(44, context.user_data["guardar_dir_existing_cust_id"])
        self.assertIn("Valor del servicio: $9,200", query.edit_calls[-1]["text"])
        self.assertIn(
            "Deseas agregar esta direccion a la agenda de Daniela?",
            query.edit_calls[-1]["text"],
        )

    def test_existing_customer_without_new_address_finishes_with_visible_value(self):
        namespace = _extract_namespace()
        namespace["get_ally_customer_by_phone"] = lambda ally_id, phone: {
            "id": 44,
            "name": "Daniela",
        }
        namespace["find_matching_customer_address"] = lambda *args, **kwargs: {"id": 99}
        query = _DummyQuery()
        update = SimpleNamespace(callback_query=query)
        context = SimpleNamespace(
            user_data={
                "service_type": "Mensajeria",
                "requires_cash": False,
                "cash_required_amount": 0,
                "customer_address": "Calle 25 # 8-19",
                "customer_city": "Pereira",
                "customer_barrio": "Cuba",
                "customer_phone": "3137481811",
                "dropoff_lat": 4.80692,
                "dropoff_lng": -75.68057,
                "pickup_city": "Pereira",
                "pickup_barrio": "Centro",
            },
            bot=_DummyBot(),
            menu_calls=[],
        )

        state = namespace["_handle_post_order_ui"](
            query,
            update,
            context,
            order_id=901,
            ally_id=7,
            published_count=1,
            pricing={},
            pickup_text="Cra 10 # 20-30",
        )

        self.assertEqual(-1, state)
        self.assertEqual(
            ["Pedido #901 creado exitosamente.\n\nValor del servicio: $9,200\n\nMercado: 1"],
            context.menu_calls,
        )
        self.assertEqual({}, context.user_data)
        self.assertEqual(1, len(query.reply_markup_calls))


if __name__ == "__main__":
    unittest.main()
