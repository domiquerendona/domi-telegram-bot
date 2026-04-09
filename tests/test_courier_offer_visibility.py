import ast
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ORDER_DELIVERY_PATH = REPO_ROOT / "Backend" / "order_delivery.py"


def _extract_namespace():
    tree = ast.parse(ORDER_DELIVERY_PATH.read_text(encoding="utf-8"))
    target_functions = {
        "_courier_visible_address_text",
        "_courier_area_text",
        "_courier_visible_location_line",
        "_get_order_visible_pickup_line",
        "_get_order_visible_dropoff_line",
        "_get_route_visible_pickup_line",
        "_get_route_stop_visible_line",
        "_get_order_missing_courier_visibility_fields",
        "_get_route_missing_courier_visibility_fields",
        "_build_offer_text",
        "_build_route_offer_text",
        "build_courier_order_preview_text",
        "build_courier_route_preview_text",
        "_build_delivery_order_suggestion",
        "build_market_launch_status_text",
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
            "No se pudieron extraer nodos esperados de order_delivery.py: {}".format(
                sorted(missing)
            )
        )

    namespace = {
        "re": re,
        "MARKET_PUBLISH_BLOCKED": -1,
        "_row_value": lambda row, key, default=None: (row or {}).get(key, default),
        "_get_pickup_address": lambda order: (order or {}).get("pickup_address", ""),
        "_get_pickup_area": lambda order: (
            (order or {}).get("pickup_city"),
            (order or {}).get("pickup_barrio"),
        ),
        "_get_dropoff_area": lambda order: (
            (order or {}).get("customer_city"),
            (order or {}).get("customer_barrio"),
        ),
        "_get_market_retry_limit": lambda: 3,
        "_coerce_market_retry_count": lambda raw, default=0: int(raw or default or 0),
        "get_fee_config": lambda: {
            "fee_service_total": 300,
            "fee_admin_share": 200,
            "fee_platform_share": 100,
        },
        "haversine_km": lambda lat1, lng1, lat2, lng2: abs(float(lat1) - float(lat2))
        + abs(float(lng1) - float(lng2)),
    }
    compiled = compile(
        ast.Module(body=selected_nodes, type_ignores=[]),
        filename=str(ORDER_DELIVERY_PATH),
        mode="exec",
    )
    exec(compiled, namespace)
    return namespace


class CourierOfferVisibilityTests(unittest.TestCase):
    def test_visible_address_helper_rejects_system_text(self):
        namespace = _extract_namespace()
        visible = namespace["_courier_visible_address_text"]

        self.assertEqual("", visible("GPS (4.80692, -75.68057)"))
        self.assertEqual("", visible("4.80692, -75.68057"))
        self.assertEqual("", visible("https://maps.google.com/?q=4.80692,-75.68057"))
        self.assertEqual("", visible("Ubicacion pendiente de detallar"))
        self.assertEqual("Calle 18 # 22-30", visible("Calle 18 # 22-30"))

    def test_visible_location_line_prefers_human_address_and_keeps_area_context(self):
        namespace = _extract_namespace()
        visible_line = namespace["_courier_visible_location_line"]

        self.assertEqual(
            "Calle 18 # 22-30 (Cuba, Pereira)",
            visible_line("Calle 18 # 22-30", "Pereira", "Cuba"),
        )
        self.assertEqual(
            "Cuba, Pereira",
            visible_line("GPS (4.80, -75.68)", "Pereira", "Cuba"),
        )

    def test_order_missing_visibility_detects_unresolvable_pickup_or_dropoff(self):
        namespace = _extract_namespace()
        missing = namespace["_get_order_missing_courier_visibility_fields"]
        order = {
            "pickup_address": "GPS (4.80, -75.68)",
            "pickup_city": "",
            "pickup_barrio": "",
            "customer_address": "Calle 25 # 8-19",
            "customer_city": "Pereira",
            "customer_barrio": "Centro",
        }

        self.assertEqual(["recogida"], missing(order))

    def test_route_missing_visibility_detects_bad_stop(self):
        namespace = _extract_namespace()
        missing = namespace["_get_route_missing_courier_visibility_fields"]
        route = {
            "pickup_address": "Cra 8 # 10-12",
            "pickup_city": "Pereira",
            "pickup_barrio": "Centro",
        }
        stops = [
            {
                "sequence": 1,
                "customer_address": "GPS (4.81, -75.67)",
                "customer_city": "",
                "customer_barrio": "",
            }
        ]

        self.assertEqual(["parada 1"], missing(route, stops))

    def test_build_offer_text_shows_visible_pickup_and_dropoff(self):
        namespace = _extract_namespace()
        build_offer = namespace["_build_offer_text"]
        order = {
            "id": 91,
            "distance_km": 3.6,
            "total_fee": 12500,
            "additional_incentive": 0,
            "payment_method": "TRANSFER_CONFIRMED",
            "cash_required_amount": 0,
            "instructions": "",
            "pickup_address": "Cra 8 # 10-12",
            "pickup_city": "Pereira",
            "pickup_barrio": "Centro",
            "customer_address": "Calle 25 # 8-19",
            "customer_city": "Pereira",
            "customer_barrio": "Cuba",
        }

        text = build_offer(order)

        self.assertIn("Recoges en: Cra 8 # 10-12 (Centro, Pereira)", text)
        self.assertIn("Entrega en: Calle 25 # 8-19 (Cuba, Pereira)", text)

    def test_build_route_offer_text_uses_visible_pickup_and_stops(self):
        namespace = _extract_namespace()
        build_route_offer = namespace["_build_route_offer_text"]
        route = {
            "id": 14,
            "pickup_address": "Cra 8 # 10-12",
            "pickup_city": "Pereira",
            "pickup_barrio": "Centro",
            "total_distance_km": 6.4,
            "total_fee": 18000,
            "additional_incentive": 0,
        }
        destinations = [
            {
                "sequence": 1,
                "customer_address": "Calle 25 # 8-19",
                "customer_city": "Pereira",
                "customer_barrio": "Cuba",
                "parking_fee": 0,
            },
            {
                "sequence": 2,
                "customer_address": "GPS (4.81, -75.67)",
                "customer_city": "Dosquebradas",
                "customer_barrio": "La Pradera",
                "parking_fee": 1200,
            },
        ]

        text = build_route_offer(route, destinations)

        self.assertIn("Recogida: Cra 8 # 10-12 (Centro, Pereira)", text)
        self.assertIn("Parada 1: Calle 25 # 8-19 (Cuba, Pereira)", text)
        self.assertIn("Parada 2: La Pradera, Dosquebradas [parqueo dificil]", text)

    def test_public_preview_helpers_wrap_real_offer_text(self):
        namespace = _extract_namespace()
        build_order_preview = namespace["build_courier_order_preview_text"]
        build_route_preview = namespace["build_courier_route_preview_text"]

        order_preview = build_order_preview(
            {
                "id": "preview",
                "distance_km": 3.6,
                "total_fee": 12500,
                "additional_incentive": 0,
                "payment_method": "TRANSFER_CONFIRMED",
                "cash_required_amount": 0,
                "instructions": "",
                "pickup_address": "Cra 8 # 10-12",
                "pickup_city": "Pereira",
                "pickup_barrio": "Centro",
                "customer_address": "Calle 25 # 8-19",
                "customer_city": "Pereira",
                "customer_barrio": "Cuba",
            }
        )
        self.assertIn("PREVIEW EXACTO DEL COURIER", order_preview)
        self.assertIn("Recoges en: Cra 8 # 10-12 (Centro, Pereira)", order_preview)

        route_preview = build_route_preview(
            {
                "id": "preview",
                "pickup_address": "Cra 8 # 10-12",
                "pickup_city": "Pereira",
                "pickup_barrio": "Centro",
                "total_distance_km": 6.4,
                "total_fee": 18000,
                "additional_incentive": 0,
            },
            [
                {
                    "sequence": 1,
                    "customer_address": "Calle 25 # 8-19",
                    "customer_city": "Pereira",
                    "customer_barrio": "Cuba",
                    "parking_fee": 0,
                }
            ],
        )
        self.assertIn("PREVIEW EXACTO DEL COURIER", route_preview)
        self.assertIn("Parada 1: Calle 25 # 8-19 (Cuba, Pereira)", route_preview)

    def test_parallel_suggestion_uses_visible_lines(self):
        namespace = _extract_namespace()
        suggestion_builder = namespace["_build_delivery_order_suggestion"]
        active_orders = [
            {
                "id": 10,
                "status": "PICKED_UP",
                "dropoff_lat": 4.81,
                "dropoff_lng": -75.67,
                "customer_address": "Calle 25 # 8-19",
                "customer_city": "Pereira",
                "customer_barrio": "Cuba",
            }
        ]
        new_order = {
            "id": 11,
            "status": "ACCEPTED",
            "dropoff_lat": 4.82,
            "dropoff_lng": -75.66,
            "pickup_address": "Cra 8 # 10-12",
            "pickup_city": "Pereira",
            "pickup_barrio": "Centro",
            "customer_address": "Avenida 30 # 15-40",
            "customer_city": "Pereira",
            "customer_barrio": "Alamos",
        }

        text = suggestion_builder(active_orders, new_order)

        self.assertIn("Entrega #10 en Calle 25 # 8-19 (Cuba, Pereira)", text)
        self.assertIn("Recoge #11 en Cra 8 # 10-12 (Centro, Pereira)", text)
        self.assertIn("Entrega #11 en Avenida 30 # 15-40 (Alamos, Pereira)", text)

    def test_market_launch_status_text_reports_blocked_publication(self):
        namespace = _extract_namespace()
        build_status = namespace["build_market_launch_status_text"]

        text = build_status(-1)

        self.assertIn("quedo bloqueada", text)
        self.assertIn("direccion visible", text)


if __name__ == "__main__":
    unittest.main()
