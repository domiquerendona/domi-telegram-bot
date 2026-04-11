import ast
import unittest
from pathlib import Path
from typing import Any, Dict


REPO_ROOT = Path(__file__).resolve().parents[1]
SERVICES_PATH = REPO_ROOT / "Backend" / "services.py"


def _extract_namespace():
    tree = ast.parse(SERVICES_PATH.read_text(encoding="utf-8"))
    target_functions = {
        "_normalize_address_match_value",
        "_default_customer_address_label",
        "find_matching_admin_customer_address",
        "upsert_customer_address_for_agenda",
        "upsert_admin_customer_address_for_agenda",
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
            "No se pudieron extraer nodos esperados de services.py: {}".format(sorted(missing))
        )

    namespace = {
        "Dict": Dict,
        "Any": Any,
        "re": __import__("re"),
        "list_admin_customer_addresses": lambda customer_id: [],
        "find_matching_customer_address": lambda customer_id, address_text, city=None, barrio=None: None,
        "create_customer_address": lambda **kwargs: 11,
        "update_customer_address": lambda **kwargs: True,
        "create_admin_customer_address": lambda **kwargs: 22,
        "update_admin_customer_address": lambda **kwargs: True,
        "has_valid_coords": lambda lat, lng: lat is not None and lng is not None,
    }

    compiled = compile(
        ast.Module(body=selected_nodes, type_ignores=[]),
        filename=str(SERVICES_PATH),
        mode="exec",
    )
    exec(compiled, namespace)
    return namespace


class AddressUpsertServiceTests(unittest.TestCase):
    def test_upsert_customer_creates_when_missing(self):
        namespace = _extract_namespace()
        create_calls = []
        namespace["create_customer_address"] = lambda **kwargs: create_calls.append(kwargs) or 99

        result = namespace["upsert_customer_address_for_agenda"](
            customer_id=44,
            label="Casa",
            address_text="  Calle 25 # 8-19 apto 302  ",
            city=" Pereira ",
            barrio=" Cuba ",
            lat=4.80692,
            lng=-75.68057,
            notes="Porteria azul",
        )

        self.assertEqual("created", result["action"])
        self.assertEqual(99, result["address_id"])
        self.assertEqual("Calle 25 # 8-19 apto 302", create_calls[0]["address_text"])
        self.assertEqual("Pereira", create_calls[0]["city"])
        self.assertEqual("Cuba", create_calls[0]["barrio"])

    def test_upsert_customer_updates_coords_when_existing_missing_gps(self):
        namespace = _extract_namespace()
        update_calls = []
        namespace["find_matching_customer_address"] = lambda *args, **kwargs: {
            "id": 7,
            "label": "Casa",
            "address_text": "Calle 25 # 8-19 apto 302",
            "city": "Pereira",
            "barrio": "Cuba",
            "notes": "Porteria azul",
            "lat": None,
            "lng": None,
        }
        namespace["update_customer_address"] = lambda **kwargs: update_calls.append(kwargs) or True

        result = namespace["upsert_customer_address_for_agenda"](
            customer_id=44,
            label="Casa",
            address_text="Calle 25 # 8-19 apto 302",
            city="Pereira",
            barrio="Cuba",
            lat=4.80692,
            lng=-75.68057,
        )

        self.assertEqual("coords_updated", result["action"])
        self.assertEqual(7, update_calls[0]["address_id"])
        self.assertEqual(4.80692, update_calls[0]["lat"])
        self.assertEqual(-75.68057, update_calls[0]["lng"])

    def test_upsert_customer_returns_existing_when_already_complete(self):
        namespace = _extract_namespace()
        namespace["find_matching_customer_address"] = lambda *args, **kwargs: {
            "id": 8,
            "label": "Casa",
            "address_text": "Calle 25 # 8-19 apto 302",
            "city": "Pereira",
            "barrio": "Cuba",
            "notes": None,
            "lat": 4.80692,
            "lng": -75.68057,
        }

        result = namespace["upsert_customer_address_for_agenda"](
            customer_id=44,
            label="Casa",
            address_text="Calle 25 # 8-19 apto 302",
            city="Pereira",
            barrio="Cuba",
            lat=4.80692,
            lng=-75.68057,
        )

        self.assertEqual("existing", result["action"])
        self.assertEqual(8, result["address_id"])

    def test_upsert_admin_creates_when_missing(self):
        namespace = _extract_namespace()
        create_calls = []
        namespace["list_admin_customer_addresses"] = lambda customer_id: []
        namespace["create_admin_customer_address"] = lambda **kwargs: create_calls.append(kwargs) or 123

        result = namespace["upsert_admin_customer_address_for_agenda"](
            customer_id=54,
            label="Casa",
            address_text="Calle 30 # 12-40",
            city="Pereira",
            barrio="Centro",
            lat=4.81,
            lng=-75.67,
            notes="Porteria",
        )

        self.assertEqual("created", result["action"])
        self.assertEqual(123, result["address_id"])
        self.assertEqual("Casa", create_calls[0]["label"])

    def test_upsert_admin_updates_coords_when_existing_missing_gps(self):
        namespace = _extract_namespace()
        update_calls = []
        namespace["list_admin_customer_addresses"] = lambda customer_id: [{
            "id": 19,
            "label": "Casa",
            "address_text": "Calle 30 # 12-40",
            "city": "Pereira",
            "barrio": "Centro",
            "notes": "Porteria",
            "lat": None,
            "lng": None,
        }]
        namespace["update_admin_customer_address"] = lambda **kwargs: update_calls.append(kwargs) or True

        result = namespace["upsert_admin_customer_address_for_agenda"](
            customer_id=54,
            label="Casa",
            address_text="Calle 30 # 12-40",
            city="Pereira",
            barrio="Centro",
            lat=4.81,
            lng=-75.67,
        )

        self.assertEqual("coords_updated", result["action"])
        self.assertEqual(19, update_calls[0]["address_id"])
        self.assertEqual(4.81, update_calls[0]["lat"])
        self.assertEqual(-75.67, update_calls[0]["lng"])


if __name__ == "__main__":
    unittest.main()
