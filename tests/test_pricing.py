"""Tests para las funciones de pricing en services.py.

Cubre: calcular_precio_distancia, build_order_pricing_breakdown,
       calcular_precio_ruta, compute_ally_subsidy.
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Backend"))

import db
import services


class PricingConfigFixture(unittest.TestCase):
    """Inicializa una BD SQLite temporal con los defaults de pricing."""

    def setUp(self):
        fd, path = tempfile.mkstemp(prefix="domi_pricing_test_", suffix=".db")
        os.close(fd)
        self.db_path = path
        os.environ["DB_PATH"] = self.db_path
        os.environ.pop("DATABASE_URL", None)
        db.init_db()

    def tearDown(self):
        try:
            os.remove(self.db_path)
        except (FileNotFoundError, PermissionError):
            pass


class CalcularPrecioDistanciaTests(PricingConfigFixture):
    """Prueba la funcion calcular_precio_distancia con los valores default de BD."""

    def _cfg(self):
        return services.get_pricing_config()

    def test_distancia_cero_retorna_cero(self):
        self.assertEqual(0, services.calcular_precio_distancia(0.0))

    def test_distancia_negativa_retorna_cero(self):
        self.assertEqual(0, services.calcular_precio_distancia(-1.0))

    def test_tier1_limite_inferior(self):
        cfg = self._cfg()
        precio = services.calcular_precio_distancia(0.5, cfg)
        self.assertEqual(cfg["precio_0_2km"], precio)

    def test_tier1_limite_superior(self):
        cfg = self._cfg()
        precio = services.calcular_precio_distancia(cfg.get("tier1_max_km", 1.5), cfg)
        self.assertEqual(cfg["precio_0_2km"], precio)

    def test_tier2(self):
        cfg = self._cfg()
        precio = services.calcular_precio_distancia(2.0, cfg)
        self.assertEqual(cfg["precio_2_3km"], precio)

    def test_distancia_extra_normal_un_km(self):
        # 3.1 km: base_distance_km=2.5, ceil(3.1-2.5)=1 km extra normal
        cfg = self._cfg()
        expected = cfg["precio_2_3km"] + 1 * cfg["precio_km_extra_normal"]
        precio = services.calcular_precio_distancia(3.1, cfg)
        self.assertEqual(expected, precio)

    def test_distancia_larga_sobre_umbral(self):
        cfg = self._cfg()
        umbral = cfg["umbral_km_largo"]
        # 1 km sobre el umbral largo
        precio_en_umbral = services.calcular_precio_distancia(umbral, cfg)
        precio_sobre_umbral = services.calcular_precio_distancia(umbral + 1.0, cfg)
        # Precio por km largo < precio por km normal => la diferencia debe ser precio_km_extra_largo
        self.assertLess(
            precio_sobre_umbral - precio_en_umbral,
            cfg["precio_km_extra_normal"],
        )

    def test_precio_aumenta_monotonamente(self):
        cfg = self._cfg()
        distancias = [0.5, 1.0, 2.0, 3.0, 4.0, 7.0, 11.0, 15.0]
        precios = [services.calcular_precio_distancia(d, cfg) for d in distancias]
        for i in range(1, len(precios)):
            self.assertGreaterEqual(
                precios[i], precios[i - 1],
                msg="Precio no monotono entre {}km y {}km".format(
                    distancias[i - 1], distancias[i]
                ),
            )


class BuildOrderPricingBreakdownTests(PricingConfigFixture):
    """Prueba build_order_pricing_breakdown: total_fee = base + distancia + buy_surcharge + incentivo."""

    def test_pedido_simple_sin_extras(self):
        result = services.build_order_pricing_breakdown(
            distance_km=1.0,
            service_type="Domicilio",
            buy_products_count=0,
            additional_incentive=0,
        )
        self.assertIn("total_fee", result)
        self.assertIn("base_fee", result)
        self.assertIn("distance_km", result)
        self.assertGreater(result["total_fee"], 0)
        # Sin incentivo: total = subtotal (distance_fee + buy_surcharge)
        self.assertEqual(
            result["subtotal_fee"] + result["additional_incentive"],
            result["total_fee"],
        )

    def test_incentivo_se_suma_al_total(self):
        base = services.build_order_pricing_breakdown(1.0, "Domicilio", 0, 0)
        con_incentivo = services.build_order_pricing_breakdown(1.0, "Domicilio", 0, 2000)
        self.assertEqual(base["total_fee"] + 2000, con_incentivo["total_fee"])
        self.assertEqual(2000, con_incentivo["additional_incentive"])

    def test_compras_tiene_surcharge(self):
        domicilio = services.build_order_pricing_breakdown(1.0, "Domicilio", 0, 0)
        compras = services.build_order_pricing_breakdown(1.0, "Compras", 3, 0)
        # Compras con productos siempre tiene buy_surcharge >= 0
        self.assertGreaterEqual(compras["buy_surcharge"], 0)
        # Con productos, el total debe ser mayor o igual que sin surcharge
        self.assertGreaterEqual(compras["total_fee"], domicilio["total_fee"])

    def test_total_fee_nunca_negativo(self):
        result = services.build_order_pricing_breakdown(0.0, "Domicilio", 0, 0)
        self.assertGreaterEqual(result["total_fee"], 0)


class CalcularPrecioRutaTests(PricingConfigFixture):
    """Prueba calcular_precio_ruta: precio base + paradas adicionales."""

    def test_ruta_una_parada_equivale_a_pedido_normal(self):
        cfg = services.get_pricing_config()
        distancia_km = 2.0
        resultado = services.calcular_precio_ruta(distancia_km, num_stops=1, config=cfg)
        precio_individual = services.calcular_precio_distancia(distancia_km, cfg)
        self.assertEqual(precio_individual, resultado["total_fee"])

    def test_paradas_adicionales_aumentan_precio(self):
        cfg = services.get_pricing_config()
        ruta_1 = services.calcular_precio_ruta(3.0, 1, cfg)
        ruta_2 = services.calcular_precio_ruta(3.0, 2, cfg)
        self.assertGreater(ruta_2["total_fee"], ruta_1["total_fee"])

    def test_retorno_tiene_campos_esperados(self):
        result = services.calcular_precio_ruta(5.0, 3)
        for campo in ("total_fee", "distance_fee", "num_stops", "additional_stops_fee"):
            self.assertIn(campo, result, msg="Campo faltante: {}".format(campo))

    def test_num_stops_se_refleja_en_resultado(self):
        result = services.calcular_precio_ruta(4.0, 3)
        self.assertEqual(3, result["num_stops"])


class ComputeAllySubsidyTests(unittest.TestCase):
    """Prueba compute_ally_subsidy: funcion pura, no necesita BD."""

    def test_sin_subsidio_retorna_cero(self):
        self.assertEqual(0, services.compute_ally_subsidy(0, None, None))

    def test_subsidio_fijo_aplica_siempre(self):
        # delivery_subsidy=2000, min_purchase=None => aplica sin importar compra
        self.assertEqual(2000, services.compute_ally_subsidy(2000, None, None))
        self.assertEqual(2000, services.compute_ally_subsidy(2000, None, 50000))

    def test_subsidio_condicional_sin_compra_no_aplica(self):
        # min_purchase=30000 pero purchase_amount=None => no aplica
        self.assertEqual(0, services.compute_ally_subsidy(3000, 30000, None))

    def test_subsidio_condicional_compra_bajo_umbral_no_aplica(self):
        self.assertEqual(0, services.compute_ally_subsidy(3000, 30000, 20000))

    def test_subsidio_condicional_compra_exacta_al_umbral_aplica(self):
        self.assertEqual(3000, services.compute_ally_subsidy(3000, 30000, 30000))

    def test_subsidio_condicional_compra_sobre_umbral_aplica(self):
        self.assertEqual(3000, services.compute_ally_subsidy(3000, 30000, 50000))

    def test_subsidio_cero_siempre_retorna_cero(self):
        # delivery_subsidy == 0 es la condicion de "sin subsidio configurado"
        self.assertEqual(0, services.compute_ally_subsidy(0, None, 100000))
        self.assertEqual(0, services.compute_ally_subsidy(0, 30000, 50000))


if __name__ == "__main__":
    unittest.main()
