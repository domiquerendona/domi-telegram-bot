import unittest

import services


class AddressDisplayServicesTests(unittest.TestCase):
    def test_is_system_address_text_detects_gps_coords_and_links(self):
        self.assertTrue(services.is_system_address_text(""))
        self.assertTrue(services.is_system_address_text("GPS (4.80692, -75.68057)"))
        self.assertTrue(services.is_system_address_text("4.80692, -75.68057"))
        self.assertTrue(services.is_system_address_text("https://maps.google.com/?q=4.80692,-75.68057"))
        self.assertFalse(services.is_system_address_text("Calle 18 # 22-30"))

    def test_visible_address_helpers_return_human_fallbacks(self):
        self.assertEqual(
            "Direccion pendiente de corregir",
            services.visible_address_text("GPS (4.80692, -75.68057)"),
        )
        self.assertEqual(
            "Calle 18 # 22-30",
            services.visible_address_text("Calle 18 # 22-30"),
        )
        self.assertEqual(
            "Calle 18 # 22-30",
            services.visible_address_label("GPS (4.80692, -75.68057)", "Calle 18 # 22-30"),
        )


if __name__ == "__main__":
    unittest.main()
