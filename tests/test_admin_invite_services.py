import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Backend"))

import db
import services


class AdminInviteServicesTests(unittest.TestCase):
    def setUp(self):
        fd, path = tempfile.mkstemp(prefix="domi_admin_invites_", suffix=".db")
        os.close(fd)
        self.db_path = path
        os.environ["DB_PATH"] = self.db_path
        os.environ.pop("DATABASE_URL", None)
        db.init_db()

        self.approved_admin_tg = 981001
        self.pending_admin_tg = 981002
        self.user = db.ensure_user(981100, "invite_target")
        self._seed_admin(self.approved_admin_tg, "APPROVED", "TEAMAI1", "Equipo Invites")
        self._seed_admin(self.pending_admin_tg, "PENDING", "TEAMAI2", "Equipo Pendiente")

    def tearDown(self):
        try:
            os.remove(self.db_path)
        except FileNotFoundError:
            pass

    def _seed_admin(self, telegram_id: int, status: str, team_code: str, team_name: str):
        user = db.ensure_user(telegram_id, f"admin_{telegram_id}")
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            f"""
            INSERT INTO admins (user_id, full_name, phone, city, barrio, status, team_name, team_code, balance)
            VALUES ({db.P}, {db.P}, {db.P}, {db.P}, {db.P}, {db.P}, {db.P}, {db.P}, 0)
            """,
            (
                user["id"],
                f"Admin {telegram_id}",
                f"300{telegram_id}",
                "Pereira",
                "Centro",
                status,
                team_name,
                team_code,
            ),
        )
        conn.commit()
        conn.close()

    def test_get_admin_registration_invites_reuses_active_tokens_and_regenerates(self):
        first = services.get_admin_registration_invites(self.approved_admin_tg, regenerate=False)
        second = services.get_admin_registration_invites(self.approved_admin_tg, regenerate=False)
        regenerated = services.get_admin_registration_invites(self.approved_admin_tg, regenerate=True)

        self.assertTrue(first["ok"])
        self.assertEqual("created", first["mode"])
        self.assertEqual("existing", second["mode"])
        self.assertEqual(first["ally_token"], second["ally_token"])
        self.assertEqual(first["courier_token"], second["courier_token"])
        self.assertNotEqual(first["ally_token"], regenerated["ally_token"])
        self.assertNotEqual(first["courier_token"], regenerated["courier_token"])
        self.assertIsNone(services.resolve_admin_invite_from_token(first["ally_token"], expected_role="ALLY"))
        self.assertIsNotNone(services.resolve_admin_invite_from_token(regenerated["ally_token"], expected_role="ALLY"))

    def test_invite_token_respects_role_scope_and_expiration(self):
        result = services.get_admin_registration_invites(self.approved_admin_tg, regenerate=False)
        ally_token = result["ally_token"]

        self.assertIsNotNone(services.resolve_admin_invite_from_token(ally_token, expected_role="ALLY"))
        self.assertIsNone(services.resolve_admin_invite_from_token(ally_token, expected_role="COURIER"))

        expired_at = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        invite_row = db.resolve_admin_invite_token(ally_token)
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            f"UPDATE admin_invite_tokens SET expires_at = {db.P} WHERE id = {db.P}",
            (expired_at, invite_row["id"]),
        )
        conn.commit()
        conn.close()

        self.assertIsNone(services.resolve_admin_invite_from_token(ally_token, expected_role="ALLY"))

    def test_non_approved_admin_cannot_get_invites(self):
        result = services.get_admin_registration_invites(self.pending_admin_tg, regenerate=False)

        self.assertFalse(result["ok"])
        self.assertIn("APPROVED", result["message"])

    def test_audit_event_only_increments_counter_on_submission(self):
        result = services.get_admin_registration_invites(self.approved_admin_tg, regenerate=False)
        ally_token = result["ally_token"]

        self.assertTrue(
            services.audit_admin_invite_event(
                ally_token,
                telegram_id=self.user["telegram_id"],
                user_id=self.user["id"],
                outcome="START_OPENED",
                note="Apertura inicial.",
            )
        )
        invite_after_open = db.resolve_admin_invite_token(ally_token)
        self.assertEqual(0, invite_after_open["uses_count"])

        self.assertTrue(
            services.audit_admin_invite_submission(
                ally_token,
                telegram_id=self.user["telegram_id"],
                user_id=self.user["id"],
                outcome="ALLY_PENDING_CREATED",
                target_role_id=321,
                note="Registro creado.",
            )
        )
        invite_after_submission = db.resolve_admin_invite_token(ally_token)
        self.assertEqual(1, invite_after_submission["uses_count"])

        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT outcome
            FROM admin_invite_token_uses
            ORDER BY id ASC
            """
        )
        outcomes = [row["outcome"] for row in cur.fetchall()]
        conn.close()
        self.assertEqual(["START_OPENED", "ALLY_PENDING_CREATED"], outcomes)


if __name__ == "__main__":
    unittest.main()
