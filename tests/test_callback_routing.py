import ast
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN_PATH = REPO_ROOT / "Backend" / "main.py"


class _MainPatternVisitor(ast.NodeVisitor):
    def __init__(self):
        self.patterns = {}

    def visit_Call(self, node):
        if not isinstance(node.func, ast.Attribute):
            return self.generic_visit(node)
        if node.func.attr != "add_handler":
            return self.generic_visit(node)
        if not node.args:
            return self.generic_visit(node)

        handler_call = node.args[0]
        if not isinstance(handler_call, ast.Call):
            return self.generic_visit(node)
        if not isinstance(handler_call.func, ast.Name):
            return self.generic_visit(node)
        if handler_call.func.id != "CallbackQueryHandler":
            return self.generic_visit(node)
        if not handler_call.args:
            return self.generic_visit(node)

        callback = handler_call.args[0]
        if not isinstance(callback, ast.Name):
            return self.generic_visit(node)

        pattern_value = None
        for keyword in handler_call.keywords:
            if keyword.arg == "pattern":
                pattern_value = self._literal_string(keyword.value)
                break

        if pattern_value is not None:
            self.patterns.setdefault(callback.id, []).append(pattern_value)

        return self.generic_visit(node)

    def _literal_string(self, node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.JoinedStr):
            return None
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left = self._literal_string(node.left)
            right = self._literal_string(node.right)
            if left is None or right is None:
                return None
            return left + right
        if isinstance(node, ast.Tuple):
            parts = [self._literal_string(elt) for elt in node.elts]
            if any(part is None for part in parts):
                return None
            return "".join(parts)
        return None


def _load_callback_patterns():
    tree = ast.parse(MAIN_PATH.read_text(encoding="utf-8"))
    visitor = _MainPatternVisitor()
    visitor.visit(tree)
    return visitor.patterns


class CallbackRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patterns = _load_callback_patterns()

    def _assert_matches(self, handler_name, samples):
        regexes = [re.compile(pattern) for pattern in self.patterns.get(handler_name, [])]
        self.assertTrue(regexes, f"No se encontraron patrones para {handler_name}.")
        for sample in samples:
            self.assertTrue(
                any(regex.match(sample) for regex in regexes),
                f"{sample} no hace match en ningun pattern de {handler_name}.",
            )

    def test_order_courier_callback_accepts_cancel_and_find_another_variants(self):
        self._assert_matches(
            "order_courier_callback",
            [
                "order_cancel_24",
                "order_cancel_confirm_24",
                "order_cancel_abort_24",
                "order_find_another_24",
                "order_find_another_confirm_24",
                "order_find_another_abort_24",
            ],
        )

    def test_handle_route_callback_accepts_route_cancel_and_wait_variants(self):
        self._assert_matches(
            "handle_route_callback",
            [
                "ruta_cancelar_aliado_24",
                "ruta_cancelar_aliado_confirm_24",
                "ruta_cancelar_aliado_abort_24",
                "ruta_find_another_24",
                "ruta_find_another_confirm_24",
                "ruta_find_another_abort_24",
                "ruta_wait_courier_24",
            ],
        )

    def test_admin_orders_callback_accepts_admin_cancel_variants(self):
        self._assert_matches(
            "admin_orders_callback",
            [
                "admpedidos_cancel_24_7",
                "admpedidos_cancel_confirm_24_7",
                "admpedidos_cancel_abort_24_7",
            ],
        )


if __name__ == "__main__":
    unittest.main()
