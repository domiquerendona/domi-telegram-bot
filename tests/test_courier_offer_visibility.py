import ast
import re
import unittest
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[1]
ORDER_DELIVERY_PATH = REPO_ROOT / "Backend" / "order_delivery.py"


def _extract_namespace():
    tree = ast.parse(ORDER_DELIVERY_PATH.read_text(encoding="utf-8"))
    target_functions = {
        "build_order_price_summary_text",
        "build_route_price_summary_text",
        "build_order_creation_summary_text",
        "build_route_creation_summary_text",
        "_get_order_courier_financials",
        "_get_route_courier_financials",
        "build_courier_order_earnings_text",
        "build_courier_route_earnings_text",
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
        "logger": SimpleNamespace(warning=lambda *args, **kwargs: None),
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

    def test_build_route_offer_text_warns_when_base_is_required(self):
        namespace = _extract_namespace()
        build_route_offer = namespace["_build_route_offer_text"]
        route = {
            "id": 15,
            "pickup_address": "Cra 8 # 10-12",
            "pickup_city": "Pereira",
            "pickup_barrio": "Centro",
            "total_distance_km": 6.4,
            "total_fee": 18000,
            "additional_incentive": 0,
            "requires_cash": True,
            "cash_required_amount": 40000,
        }

        text = build_route_offer(
            route,
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

        self.assertIn("Base requerida: $40,000", text)
        self.assertEqual(1, text.count("Base requerida: $40,000"))
        self.assertIn("NO tomes esta ruta", text)

    def test_build_order_offer_text_warns_when_base_is_required_without_duplicate_base(self):
        namespace = _extract_namespace()
        build_offer = namespace["_build_offer_text"]
        order = {
            "id": 92,
            "distance_km": 4.1,
            "total_fee": 13200,
            "additional_incentive": 500,
            "parking_fee": 0,
            "payment_method": "CASH_CONFIRMED",
            "requires_cash": True,
            "cash_required_amount": 25000,
            "instructions": "",
            "pickup_address": "Cra 8 # 10-12",
            "pickup_city": "Pereira",
            "pickup_barrio": "Centro",
            "customer_address": "Calle 25 # 8-19",
            "customer_city": "Pereira",
            "customer_barrio": "Cuba",
        }

        text = build_offer(order)

        self.assertIn("Pago total del pedido: $13,200", text)
        self.assertIn("Neto esperado: $12,900", text)
        self.assertIn("Base requerida: $25,000", text)
        self.assertEqual(1, text.count("Base requerida: $25,000"))
        self.assertIn("NO tomes este servicio", text)

    def test_order_price_summary_keeps_total_incentive_and_parking(self):
        namespace = _extract_namespace()
        summary = namespace["build_order_price_summary_text"]
        order = {
            "total_fee": 12800,
            "additional_incentive": 1500,
            "parking_fee": 800,
            "requires_cash": True,
            "cash_required_amount": 20000,
        }

        text = summary(order, label="Valor del servicio")

        self.assertIn("Valor del servicio: $12,800", text)
        self.assertIn("Incluye incentivo: +$1,500", text)
        self.assertIn("Incluye parqueo dificil: +$800", text)
        self.assertIn("Base requerida: $20,000", text)

    def test_order_price_summary_logs_warning_when_total_is_missing(self):
        namespace = _extract_namespace()
        warnings = []
        namespace["logger"] = SimpleNamespace(
            warning=lambda message, *args: warnings.append(message % args if args else message)
        )
        summary = namespace["build_order_price_summary_text"]

        text = summary({"id": 88, "total_fee": 0}, label="Valor del servicio")

        self.assertIn("Valor del servicio: $0", text)
        self.assertTrue(any("total_fee no visible order_id=88" in warning for warning in warnings))

    def test_route_price_summary_keeps_total_and_incentive(self):
        namespace = _extract_namespace()
        summary = namespace["build_route_price_summary_text"]
        route = {
            "total_fee": 21000,
            "additional_incentive": 3000,
        }

        text = summary(route, label="Valor de la ruta")

        self.assertIn("Valor de la ruta: $21,000", text)
        self.assertIn("Incluye incentivo: +$3,000", text)

    def test_route_price_summary_logs_warning_when_total_is_missing(self):
        namespace = _extract_namespace()
        warnings = []
        namespace["logger"] = SimpleNamespace(
            warning=lambda message, *args: warnings.append(message % args if args else message)
        )
        summary = namespace["build_route_price_summary_text"]

        text = summary({"id": 41, "total_fee": 0}, label="Valor de la ruta")

        self.assertIn("Valor de la ruta: $0", text)
        self.assertTrue(any("total_fee no visible route_id=41" in warning for warning in warnings))

    def test_creation_summaries_keep_visible_value(self):
        namespace = _extract_namespace()
        build_order_summary = namespace["build_order_creation_summary_text"]
        build_route_summary = namespace["build_route_creation_summary_text"]

        order_text = build_order_summary(
            {"id": 91, "total_fee": 9200, "additional_incentive": 0, "parking_fee": 0},
            "Estamos buscando repartidor cerca.",
        )
        route_text = build_route_summary(
            {"id": 14, "total_fee": 18000, "additional_incentive": 2000},
            "Estamos buscando repartidor cerca.",
        )

        self.assertIn("Pedido #91 creado exitosamente.", order_text)
        self.assertIn("Valor del servicio: $9,200", order_text)
        self.assertIn("Estamos buscando repartidor cerca.", order_text)
        self.assertIn("Ruta #14 creada.", route_text)
        self.assertIn("Valor de la ruta: $18,000", route_text)
        self.assertIn("Incluye incentivo: +$2,000", route_text)

    def test_courier_order_earnings_text_shows_expected_net(self):
        namespace = _extract_namespace()
        summary = namespace["build_courier_order_earnings_text"]
        order = {
            "total_fee": 12500,
            "additional_incentive": 1500,
            "parking_fee": 800,
            "special_commission": 2000,
        }

        text = summary(order)

        self.assertIn("Pago total del pedido: $12,500", text)
        self.assertIn("Total descuento: -$2,300", text)
        self.assertIn("Neto esperado: $10,200", text)

    def test_courier_route_earnings_text_shows_expected_net(self):
        namespace = _extract_namespace()
        summary = namespace["build_courier_route_earnings_text"]
        route = {
            "total_fee": 18000,
            "additional_incentive": 1000,
        }

        text = summary(route)

        self.assertIn("Pago total de la ruta: $18,000", text)
        self.assertIn("Descuento al entregar: -$300", text)
        self.assertIn("Neto esperado: $17,700", text)

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
