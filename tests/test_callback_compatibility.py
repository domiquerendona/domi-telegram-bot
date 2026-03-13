import unittest

import services


class CallbackCompatibilityTests(unittest.TestCase):
    def test_parse_ally_team_legacy_format(self):
        self.assertEqual("TEAM1", services.parse_team_selection_callback("ally_team:TEAM1", "ally_team"))

    def test_parse_ally_team_modern_format(self):
        self.assertEqual("TEAM1", services.parse_team_selection_callback("ally_team_TEAM1", "ally_team"))

    def test_parse_courier_team_legacy_format(self):
        self.assertEqual("TEAM2", services.parse_team_selection_callback("courier_team:TEAM2", "courier_team"))

    def test_parse_courier_team_modern_format(self):
        self.assertEqual("TEAM2", services.parse_team_selection_callback("courier_team_TEAM2", "courier_team"))

    def test_parse_team_selection_returns_none_for_invalid_prefix(self):
        self.assertIsNone(services.parse_team_selection_callback("courier_pick_admin_7", "courier_team"))


if __name__ == "__main__":
    unittest.main()
