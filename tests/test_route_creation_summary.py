import ast
import ast
import unittest
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[1]
ROUTE_HANDLER_PATH = REPO_ROOT / "Backend" / "handlers" / "route.py"


class _DummyQuery:
    def __init__(self, data="ruta_confirmar"):
        self.data = data
        self.answer_calls = 0
        self.edit_calls = []

    def answer(self):
        self.answer_calls += 1

    def edit_message_text(self, text, reply_markup=None):
        self.edit_calls.append({"text": text, "reply_markup": reply_markup})


def _extract_namespace():
    tree = ast.parse(ROUTE_HANDLER_PATH.read_text(encoding="utf-8"))
    target_functions = {"ruta_confirmacion_callback"}

    selected_nodes = []
    found = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in target_functions:
            selected_nodes.append(node)
            found.add(node.name)

    missing = target_functions - found
    if missing:
        raise AssertionError(
            "No se pudieron extraer nodos esperados de route.py: {}".format(
                sorted(missing)
            )
        )

    namespace = {
        "RUTA_CONFIRMACION": 61,
        "ConversationHandler": SimpleNamespace(END=-1),
        "has_valid_coords": lambda lat, lng: lat is not None and lng is not None,
        "get_approved_admin_link_for_ally": lambda ally_id: {"admin_id": 11},
        "get_ally_link_balance": lambda ally_id, admin_id: 5000,
        "create_route": lambda **kwargs: 55,
        "create_route_destination": lambda **kwargs: None,
        "add_route_incentive": lambda route_id, incentive: None,
        "publish_route_to_couriers": lambda route_id, ally_id, context, admin_id_override=None: 3,
        "get_route_by_id": lambda route_id: {
            "id": route_id,
            "total_fee": 6500,
            "additional_incentive": 1700,
        },
        "build_market_launch_status_text": lambda count: "Mercado: {}".format(count),
        "build_route_creation_summary_text": (
            lambda route, market_status_text: (
                "Ruta #{} creada.\n\nValor de la ruta: ${:,}\nIncluye incentivo: +$1,700\n\n{}".format(
                    route["id"],
                    int(route["total_fee"] or 0),
                    market_status_text,
                )
            )
        ),
        "show_main_menu": lambda update, context: context.menu_calls.append("shown"),
        "logger": SimpleNamespace(error=lambda *args, **kwargs: None),
    }

    compiled = compile(
        ast.Module(body=selected_nodes, type_ignores=[]),
        filename=str(ROUTE_HANDLER_PATH),
        mode="exec",
    )
    exec(compiled, namespace)
    return namespace


class RouteCreationSummaryTests(unittest.TestCase):
    def test_route_confirmation_success_keeps_visible_value(self):
        namespace = _extract_namespace()
        query = _DummyQuery()
        update = SimpleNamespace(callback_query=query)
        context = SimpleNamespace(
            user_data={
                "ruta_ally_id": 7,
                "ruta_paradas": [
                    {
                        "name": "Daniela",
                        "phone": "3137481811",
                        "address": "Calle 25 # 8-19",
                        "city": "Pereira",
                        "barrio": "Cuba",
                        "lat": 4.80692,
                        "lng": -75.68057,
                        "parking_fee": 0,
                    },
                    {
                        "name": "Mateo",
                        "phone": "3130000000",
                        "address": "Cra 8 # 10-12",
                        "city": "Dosquebradas",
                        "barrio": "La Pradera",
                        "lat": 4.84,
                        "lng": -75.66,
                        "parking_fee": 1200,
                    },
                ],
                "ruta_precio": {
                    "distance_fee": 4200,
                    "additional_stops_fee": 600,
                    "total_fee": 6500,
                },
                "ruta_pickup_address": "Cra 10 # 20-30",
                "ruta_pickup_lat": 4.81,
                "ruta_pickup_lng": -75.67,
                "ruta_pickup_location_id": 15,
                "ruta_distancia_km": 6.4,
                "ruta_requires_cash": False,
                "ruta_cash_required_amount": 0,
                "ruta_incentivo": 1700,
            },
            menu_calls=[],
        )

        state = namespace["ruta_confirmacion_callback"](update, context)

        self.assertEqual(-1, state)
        self.assertIn("Ruta #55 creada.", query.edit_calls[-1]["text"])
        self.assertIn("Valor de la ruta: $6,500", query.edit_calls[-1]["text"])
        self.assertIn("Incluye incentivo: +$1,700", query.edit_calls[-1]["text"])
        self.assertIn("Mercado: 3", query.edit_calls[-1]["text"])
        self.assertEqual(["shown"], context.menu_calls)
        self.assertEqual({}, context.user_data)


if __name__ == "__main__":
    unittest.main()
