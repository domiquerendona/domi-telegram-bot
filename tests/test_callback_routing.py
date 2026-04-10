import ast
import re
import unittest
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN_PATH = REPO_ROOT / "Backend" / "main.py"
ORDER_HANDLER_PATH = REPO_ROOT / "Backend" / "handlers" / "order.py"
CUSTOMER_AGENDA_PATH = REPO_ROOT / "Backend" / "handlers" / "customer_agenda.py"
LOCATION_AGENDA_PATH = REPO_ROOT / "Backend" / "handlers" / "location_agenda.py"


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


class _InlineKeyboardButton:
    def __init__(self, text, callback_data=None):
        self.text = text
        self.callback_data = callback_data


class _InlineKeyboardMarkup:
    def __init__(self, keyboard):
        self.inline_keyboard = keyboard


class _DummyQuery:
    def __init__(self, data):
        self.data = data
        self.answer_calls = 0
        self.edit_calls = []

    def answer(self):
        self.answer_calls += 1

    def edit_message_text(self, text, reply_markup=None):
        self.edit_calls.append({"text": text, "reply_markup": reply_markup})


def _extract_order_base_namespace():
    tree = ast.parse(ORDER_HANDLER_PATH.read_text(encoding="utf-8"))
    target_assignments = {"PEDIDO_BASE_PRESET_AMOUNTS", "PEDIDO_BASE_CALLBACK_PATTERN"}
    target_functions = {
        "_pedido_base_keyboard",
        "_pedido_base_flow_kind",
        "_pedido_base_storage_keys",
        "_pedido_set_base_requirement",
        "_pedido_payment_method_from_base",
        "_pedido_continue_after_base",
        "pedido_requiere_base_callback",
        "pedido_valor_base_callback",
    }
    selected_nodes = []
    found_assignments = set()
    found_functions = set()

    for node in tree.body:
        if isinstance(node, ast.Assign):
            target_names = {
                target.id for target in node.targets if isinstance(target, ast.Name)
            }
            matches = target_names & target_assignments
            if matches:
                selected_nodes.append(node)
                found_assignments.update(matches)
        elif isinstance(node, ast.FunctionDef) and node.name in target_functions:
            selected_nodes.append(node)
            found_functions.add(node.name)

    missing = (target_assignments - found_assignments) | (target_functions - found_functions)
    if missing:
        raise AssertionError(
            "No se pudieron extraer nodos esperados de order.py: {}".format(sorted(missing))
        )

    namespace = {
        "InlineKeyboardButton": _InlineKeyboardButton,
        "InlineKeyboardMarkup": _InlineKeyboardMarkup,
        "_fmt_pesos": lambda amount: f"${int(amount):,}".replace(",", "."),
        "_admin_pedido_calcular_preview": lambda query, context, edit=False: "admin_preview_ok",
        "_ruta_continue_after_base": lambda query, context, edit=False: "ruta_continue_ok",
        "calcular_cotizacion_y_confirmar": lambda query, context, edit=False: "cotizacion_ok",
        "PEDIDO_VALOR_BASE": 970,
        "PEDIDO_REQUIERE_BASE": 969,
    }
    compiled = compile(
        ast.Module(body=selected_nodes, type_ignores=[]),
        filename=str(ORDER_HANDLER_PATH),
        mode="exec",
    )
    exec(compiled, namespace)
    return namespace


def _load_conversation_state_names(conversation_name):
    tree = ast.parse(ORDER_HANDLER_PATH.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        target_names = {target.id for target in node.targets if isinstance(target, ast.Name)}
        if conversation_name not in target_names:
            continue
        if not isinstance(node.value, ast.Call):
            continue
        if not isinstance(node.value.func, ast.Name) or node.value.func.id != "ConversationHandler":
            continue
        for keyword in node.value.keywords:
            if keyword.arg != "states" or not isinstance(keyword.value, ast.Dict):
                continue
            state_names = []
            for key in keyword.value.keys:
                if isinstance(key, ast.Name):
                    state_names.append(key.id)
            return state_names
    raise AssertionError(f"No se pudo encontrar la conversacion {conversation_name}.")


def _load_conversation_entry_patterns_from_path(path, conversation_name):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        target_names = {target.id for target in node.targets if isinstance(target, ast.Name)}
        if conversation_name not in target_names:
            continue
        if not isinstance(node.value, ast.Call):
            continue
        if not isinstance(node.value.func, ast.Name) or node.value.func.id != "ConversationHandler":
            continue
        for keyword in node.value.keywords:
            if keyword.arg != "entry_points" or not isinstance(keyword.value, ast.List):
                continue
            patterns = []
            for item in keyword.value.elts:
                if not isinstance(item, ast.Call):
                    continue
                for call_keyword in item.keywords:
                    if call_keyword.arg == "pattern" and isinstance(call_keyword.value, ast.Constant):
                        patterns.append(call_keyword.value.value)
            return patterns
    raise AssertionError(f"No se pudo encontrar entry_points para la conversacion {conversation_name}.")


def _load_conversation_entry_patterns(conversation_name):
    return _load_conversation_entry_patterns_from_path(ORDER_HANDLER_PATH, conversation_name)


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

    def test_admin_pedido_conv_entry_accepts_legacy_and_explicit_admin_id(self):
        patterns = [re.compile(pattern) for pattern in _load_conversation_entry_patterns("admin_pedido_conv")]
        self.assertTrue(any(pattern.match("admin_nuevo_pedido") for pattern in patterns))
        self.assertTrue(any(pattern.match("admin_nuevo_pedido_7") for pattern in patterns))

    def test_admin_panel_callbacks_accept_explicit_admin_id(self):
        self._assert_matches(
            "admin_mi_saldo_callback",
            ["admin_mi_saldo_7"],
        )
        self._assert_matches(
            "admin_movimientos_callback",
            ["admin_movimientos_7"],
        )
        self._assert_matches(
            "admin_movimientos_periodo_callback",
            ["admin_movimientos_mes_7", "admin_movimientos_soc_mes_7"],
        )
        self._assert_matches(
            "admin_mis_plantillas_callback",
            ["admin_mis_plantillas_7"],
        )
        self._assert_matches(
            "admin_ped_tmpl_info_callback",
            ["admin_ped_tmpl_info_11_7"],
        )
        self._assert_matches(
            "admin_ped_tmpl_menu_del_callback",
            ["admin_ped_tmpl_menu_del_11_7"],
        )

    def test_admin_clientes_and_dirs_conversations_accept_explicit_admin_id(self):
        clientes_patterns = [
            re.compile(pattern)
            for pattern in _load_conversation_entry_patterns_from_path(
                CUSTOMER_AGENDA_PATH,
                "admin_clientes_conv",
            )
        ]
        dirs_patterns = [
            re.compile(pattern)
            for pattern in _load_conversation_entry_patterns_from_path(
                LOCATION_AGENDA_PATH,
                "admin_dirs_conv",
            )
        ]
        self.assertTrue(any(pattern.match("admin_mis_clientes_7") for pattern in clientes_patterns))
        self.assertTrue(any(pattern.match("admin_mis_dirs_7") for pattern in dirs_patterns))

    def test_main_menu_emits_explicit_admin_callbacks_for_admin_panel(self):
        source = MAIN_PATH.read_text(encoding="utf-8")

        for callback_template in [
            "admin_nuevo_pedido_{}",
            "adminhist_periodo_hoy_{}",
            "admin_mis_clientes_{}",
            "admin_mis_dirs_{}",
            "admin_mis_plantillas_{}",
            "admin_mi_saldo_{}",
            "admin_movimientos_{}",
            "admin_sociedad_retiro_{}",
        ]:
            self.assertIn(callback_template, source)

    def test_admin_menu_callback_does_not_match_special_order_internal_callbacks(self):
        regexes = [re.compile(pattern) for pattern in self.patterns.get("admin_menu_callback", [])]
        self.assertTrue(regexes, "No se encontraron patrones para admin_menu_callback.")

        for sample in [
            "admin_pedido_pickup_7",
            "admin_pedido_nueva_dir",
            "admin_pedido_geo_pickup_si",
            "admin_pedido_confirmar",
        ]:
            self.assertFalse(
                any(regex.match(sample) for regex in regexes),
                f"{sample} no deberia hacer match en admin_menu_callback.",
            )


class PedidoBaseFlowTests(unittest.TestCase):
    def _load_namespace(self):
        return _extract_order_base_namespace()

    def test_pedido_base_keyboard_shows_expected_buttons(self):
        namespace = self._load_namespace()

        markup = namespace["_pedido_base_keyboard"]()
        buttons = [
            [(button.text, button.callback_data) for button in row]
            for row in markup.inline_keyboard
        ]

        self.assertEqual(
            [
                [("$20.000", "pedido_base_20000"), ("$50.000", "pedido_base_50000")],
                [("$100.000", "pedido_base_100000"), ("$200.000", "pedido_base_200000")],
                [("Otro valor", "pedido_base_otro")],
            ],
            buttons,
        )

    def test_pedido_base_callback_pattern_matches_current_supported_values(self):
        namespace = self._load_namespace()
        pattern = re.compile(namespace["PEDIDO_BASE_CALLBACK_PATTERN"])

        for allowed in [
            "pedido_base_20000",
            "pedido_base_50000",
            "pedido_base_100000",
            "pedido_base_200000",
            "pedido_base_otro",
        ]:
            self.assertIsNotNone(pattern.match(allowed), allowed)

        for rejected in [
            "pedido_base_5000",
            "pedido_base_10000",
            "pedido_base_30000",
            "pedido_base_otra",
        ]:
            self.assertIsNone(pattern.match(rejected), rejected)

    def test_pedido_valor_base_callback_saves_supported_preset_amount(self):
        namespace = self._load_namespace()
        calls = []

        def _fake_calcular(query, context, edit=False):
            calls.append((query, context, edit))
            return "cotizacion_ok"

        namespace["calcular_cotizacion_y_confirmar"] = _fake_calcular
        query = _DummyQuery("pedido_base_100000")
        update = SimpleNamespace(callback_query=query)
        context = SimpleNamespace(user_data={})

        result = namespace["pedido_valor_base_callback"](update, context)

        self.assertEqual(1, query.answer_calls)
        self.assertEqual(100000, context.user_data["cash_required_amount"])
        self.assertEqual("cotizacion_ok", result)
        self.assertEqual([(query, context, True)], calls)
        self.assertEqual([], query.edit_calls)

    def test_pedido_base_no_in_admin_flow_uses_admin_keys_and_preview_dispatch(self):
        namespace = self._load_namespace()
        query = _DummyQuery("pedido_base_no")
        update = SimpleNamespace(callback_query=query)
        context = SimpleNamespace(user_data={"admin_ped_admin_id": 11})

        result = namespace["pedido_requiere_base_callback"](update, context)

        self.assertEqual(1, query.answer_calls)
        self.assertFalse(context.user_data["admin_ped_requires_cash"])
        self.assertEqual(0, context.user_data["admin_ped_cash_required_amount"])
        self.assertEqual("admin_preview_ok", result)

    def test_pedido_base_preset_in_route_flow_uses_route_keys_and_dispatch(self):
        namespace = self._load_namespace()
        query = _DummyQuery("pedido_base_50000")
        update = SimpleNamespace(callback_query=query)
        context = SimpleNamespace(user_data={"ruta_ally_id": 44})

        result = namespace["pedido_valor_base_callback"](update, context)

        self.assertEqual(1, query.answer_calls)
        self.assertTrue(context.user_data["ruta_requires_cash"])
        self.assertEqual(50000, context.user_data["ruta_cash_required_amount"])
        self.assertEqual("ruta_continue_ok", result)

    def test_pedido_valor_base_callback_otro_requests_manual_amount(self):
        namespace = self._load_namespace()
        calc_calls = []
        namespace["calcular_cotizacion_y_confirmar"] = lambda *args, **kwargs: calc_calls.append(
            (args, kwargs)
        )
        query = _DummyQuery("pedido_base_otro")
        update = SimpleNamespace(callback_query=query)
        context = SimpleNamespace(user_data={})

        result = namespace["pedido_valor_base_callback"](update, context)

        self.assertEqual(1, query.answer_calls)
        self.assertEqual(namespace["PEDIDO_VALOR_BASE"], result)
        self.assertEqual([], calc_calls)
        self.assertEqual(
            [{"text": "Escribe el valor de la base (solo numeros):", "reply_markup": None}],
            query.edit_calls,
        )
        self.assertEqual({}, context.user_data)

    def test_admin_pedido_conv_includes_shared_base_states(self):
        state_names = _load_conversation_state_names("admin_pedido_conv")

        self.assertIn("PEDIDO_REQUIERE_BASE", state_names)
        self.assertIn("PEDIDO_VALOR_BASE", state_names)


if __name__ == "__main__":
    unittest.main()
