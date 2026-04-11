import ast
import unittest
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[1]
CUSTOMER_AGENDA_PATH = REPO_ROOT / "Backend" / "handlers" / "customer_agenda.py"


class _DummyMessage:
    def __init__(self):
        self.reply_calls = []

    def reply_text(self, text, reply_markup=None):
        self.reply_calls.append({"text": text, "reply_markup": reply_markup})


def _extract_namespace():
    tree = ast.parse(CUSTOMER_AGENDA_PATH.read_text(encoding="utf-8"))
    target_functions = {
        "_agenda_address_upsert_feedback",
        "clientes_dir_barrio_handler",
        "admin_clientes_dir_barrio_handler",
        "ally_clientes_dir_barrio_handler",
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
            "No se pudieron extraer nodos esperados de customer_agenda.py: {}".format(sorted(missing))
        )

    namespace = {
        "CLIENTES_DIR_BARRIO": 201,
        "CLIENTES_MENU": 202,
        "ADMIN_CUST_DIR_BARRIO": 301,
        "ADMIN_CUST_MENU": 302,
        "ALLY_CUST_DIR_BARRIO": 401,
        "ALLY_CUST_MENU": 402,
        "_handle_text_field_input": lambda *args, **kwargs: 999,
        "clientes_mostrar_menu": lambda update, context, edit_message=False: 202,
        "_admin_clientes_mostrar_menu": lambda update, context, edit_message=False: 302,
        "_ally_clientes_mostrar_menu": lambda update, context, edit_message=False: 402,
        "upsert_customer_address_for_agenda": lambda **kwargs: {
            "action": "created",
            "address_id": 1,
            "address": None,
        },
        "upsert_admin_customer_address_for_agenda": lambda **kwargs: {
            "action": "created",
            "address_id": 2,
            "address": None,
        },
        "create_ally_customer": lambda *args, **kwargs: 10,
        "create_customer_address": lambda *args, **kwargs: 20,
        "create_admin_customer": lambda *args, **kwargs: 30,
        "create_admin_customer_address": lambda *args, **kwargs: 40,
        "get_ally_parking_fee_enabled": lambda ally_id: False,
        "InlineKeyboardButton": object,
        "InlineKeyboardMarkup": object,
    }

    compiled = compile(
        ast.Module(body=selected_nodes, type_ignores=[]),
        filename=str(CUSTOMER_AGENDA_PATH),
        mode="exec",
    )
    exec(compiled, namespace)
    return namespace


class CustomerAgendaAddressUpsertTests(unittest.TestCase):
    def test_clientes_dir_nueva_creates_new_address(self):
        namespace = _extract_namespace()
        update = SimpleNamespace(message=_DummyMessage())
        context = SimpleNamespace(
            user_data={
                "clientes_pending_barrio": "Cuba",
                "clientes_pending_mode": "dir_nueva",
                "clientes_pending_address_text": "Calle 25 # 8-19 apto 302",
                "clientes_pending_lat": 4.80692,
                "clientes_pending_lng": -75.68057,
                "clientes_pending_city": "Pereira",
                "clientes_pending_notes": None,
                "current_customer_id": 44,
                "new_address_label": "Casa",
            }
        )

        state = namespace["clientes_dir_barrio_handler"](update, context)

        self.assertEqual(202, state)
        self.assertIn("Direccion guardada: Casa - Calle 25 # 8-19 apto 302", update.message.reply_calls[-1]["text"])

    def test_admin_clientes_dir_nueva_backfills_coords(self):
        namespace = _extract_namespace()
        calls = []
        namespace["upsert_admin_customer_address_for_agenda"] = (
            lambda **kwargs: calls.append(kwargs) or {
                "action": "coords_updated",
                "address_id": 9,
                "address": None,
            }
        )
        update = SimpleNamespace(message=_DummyMessage())
        context = SimpleNamespace(
            user_data={
                "acust_pending_barrio": "Cuba",
                "acust_pending_mode": "dir_nueva",
                "acust_pending_address_text": "Calle 25 # 8-19 apto 302",
                "acust_pending_lat": 4.80692,
                "acust_pending_lng": -75.68057,
                "acust_pending_city": "Pereira",
                "acust_pending_notes": "Porteria azul",
                "acust_current_customer_id": 54,
                "acust_new_address_label": "Casa",
            }
        )

        state = namespace["admin_clientes_dir_barrio_handler"](update, context)

        self.assertEqual(302, state)
        self.assertEqual(54, calls[0]["customer_id"])
        self.assertEqual("Pereira", calls[0]["city"])
        self.assertEqual("Cuba", calls[0]["barrio"])
        self.assertIn("se completo su geolocalizacion", update.message.reply_calls[-1]["text"])

    def test_ally_clientes_dir_nueva_detects_existing_address(self):
        namespace = _extract_namespace()
        calls = []
        namespace["upsert_customer_address_for_agenda"] = (
            lambda **kwargs: calls.append(kwargs) or {
                "action": "existing",
                "address_id": 11,
                "address": None,
            }
        )
        update = SimpleNamespace(message=_DummyMessage())
        context = SimpleNamespace(
            user_data={
                "allycust_pending_barrio": "Cuba",
                "allycust_pending_mode": "dir_nueva",
                "allycust_pending_address_text": "Calle 25 # 8-19 apto 302",
                "allycust_pending_lat": 4.80692,
                "allycust_pending_lng": -75.68057,
                "allycust_pending_city": "Pereira",
                "allycust_pending_notes": None,
                "allycust_current_customer_id": 64,
                "allycust_new_address_label": "Casa",
            }
        )

        state = namespace["ally_clientes_dir_barrio_handler"](update, context)

        self.assertEqual(402, state)
        self.assertEqual(64, calls[0]["customer_id"])
        self.assertIn("ya estaba guardada", update.message.reply_calls[-1]["text"])


if __name__ == "__main__":
    unittest.main()
