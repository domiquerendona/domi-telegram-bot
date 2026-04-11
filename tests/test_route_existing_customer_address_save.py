import ast
import unittest
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[1]
ROUTE_HANDLER_PATH = REPO_ROOT / "Backend" / "handlers" / "route.py"


class _InlineKeyboardButton:
    def __init__(self, text, callback_data=None):
        self.text = text
        self.callback_data = callback_data


class _InlineKeyboardMarkup:
    def __init__(self, keyboard):
        self.inline_keyboard = keyboard


class _DummyMessage:
    def __init__(self):
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
    tree = ast.parse(ROUTE_HANDLER_PATH.read_text(encoding="utf-8"))
    target_functions = {
        "_ruta_guardar_parada_y_cliente",
        "ruta_guardar_cust_callback",
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
            "No se pudieron extraer nodos esperados de route.py: {}".format(sorted(missing))
        )

    namespace = {
        "InlineKeyboardButton": _InlineKeyboardButton,
        "InlineKeyboardMarkup": _InlineKeyboardMarkup,
        "RUTA_GUARDAR_CLIENTES": 50,
        "RUTA_GUARDAR_CUST_PARKING": 51,
        "logger": SimpleNamespace(warning=lambda *args, **kwargs: None),
        "find_matching_customer_address": lambda *args, **kwargs: None,
        "upsert_customer_address_for_agenda": lambda **kwargs: {
            "action": "created",
            "address_id": 1,
            "address": None,
        },
        "get_ally_customer_by_phone": lambda ally_id, phone: None,
        "create_ally_customer": lambda ally_id, name, phone: 77,
        "get_ally_parking_fee_enabled": lambda ally_id: False,
        "has_valid_coords": lambda lat, lng: lat is not None and lng is not None,
        "_ruta_mostrar_mas_paradas": lambda target, context: 99,
        "RUTA_PARADA_SELECTOR": 1,
    }

    def _ruta_guardar_parada_actual(context):
        parada = {
            "name": context.user_data.get("ruta_temp_name") or "",
            "phone": context.user_data.get("ruta_temp_phone") or "",
            "address": context.user_data.get("ruta_temp_address") or "",
            "city": context.user_data.get("ruta_temp_city") or "",
            "barrio": context.user_data.get("ruta_temp_barrio") or "",
            "lat": context.user_data.get("ruta_temp_lat"),
            "lng": context.user_data.get("ruta_temp_lng"),
            "customer_id": context.user_data.get("ruta_temp_customer_id"),
            "parking_fee": int(context.user_data.get("ruta_temp_parking_fee") or 0),
        }
        paradas = context.user_data.get("ruta_paradas", [])
        paradas.append(parada)
        context.user_data["ruta_paradas"] = paradas

    namespace["_ruta_guardar_parada_actual"] = _ruta_guardar_parada_actual

    compiled = compile(
        ast.Module(body=selected_nodes, type_ignores=[]),
        filename=str(ROUTE_HANDLER_PATH),
        mode="exec",
    )
    exec(compiled, namespace)
    return namespace


class RouteExistingCustomerAddressSaveTests(unittest.TestCase):
    def test_existing_customer_new_address_prompts_save(self):
        namespace = _extract_namespace()
        context = SimpleNamespace(
            user_data={
                "ruta_paradas": [],
                "ruta_temp_customer_id": 44,
                "ruta_temp_name": "Daniela",
                "ruta_temp_phone": "3137481811",
                "ruta_temp_address": "Calle 25 # 8-19 apto 302",
                "ruta_temp_city": "Pereira",
                "ruta_temp_barrio": "Cuba",
                "ruta_temp_lat": 4.80692,
                "ruta_temp_lng": -75.68057,
            }
        )
        query = _DummyQuery()

        state = namespace["_ruta_guardar_parada_y_cliente"](context, query)

        self.assertEqual(50, state)
        self.assertIn("Deseas guardar esta direccion", query.edit_calls[-1]["text"])
        buttons = query.edit_calls[-1]["reply_markup"].inline_keyboard
        self.assertEqual("ruta_guardar_cust_si", buttons[0][0].callback_data)

    def test_existing_customer_save_uses_geolocated_upsert(self):
        namespace = _extract_namespace()
        upsert_calls = []
        namespace["upsert_customer_address_for_agenda"] = (
            lambda **kwargs: upsert_calls.append(kwargs) or {
                "action": "created",
                "address_id": 88,
                "address": None,
            }
        )

        query = _DummyQuery("ruta_guardar_cust_si")
        update = SimpleNamespace(callback_query=query)
        context = SimpleNamespace(
            user_data={
                "ruta_ally_id": 7,
                "ruta_paradas": [
                    {
                        "customer_id": 44,
                        "name": "Daniela",
                        "phone": "3137481811",
                        "address": "Calle 25 # 8-19 apto 302",
                        "city": "Pereira",
                        "barrio": "Cuba",
                        "lat": 4.80692,
                        "lng": -75.68057,
                    }
                ],
            }
        )

        state = namespace["ruta_guardar_cust_callback"](update, context)

        self.assertEqual(99, state)
        self.assertEqual(44, upsert_calls[0]["customer_id"])
        self.assertEqual("Pereira", upsert_calls[0]["city"])
        self.assertEqual("Cuba", upsert_calls[0]["barrio"])
        self.assertEqual(4.80692, upsert_calls[0]["lat"])
        self.assertEqual(-75.68057, upsert_calls[0]["lng"])
        self.assertIn("Direccion guardada para Daniela.", query.edit_calls[-1]["text"])


if __name__ == "__main__":
    unittest.main()
