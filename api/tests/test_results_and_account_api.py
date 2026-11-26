import datetime
import json

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase

from api.auth import create_access_token, hash_refresh_token
from api.models import DevicePushToken, RefreshToken
from ladder.models import Ladder, LadderSubscription, League, Player, Result, Season


class ResultsAndAccountApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Result.objects.all().delete()
        League.objects.all().delete()
        Ladder.objects.all().delete()
        Season.objects.all().delete()
        Player.objects.all().delete()

        cls.user1 = User.objects.create_user(
            username="alice@example.com",
            email="alice@example.com",
            password="OldPassword123!",
            first_name="Alice",
            last_name="Smith",
        )
        cls.user2 = User.objects.create_user(
            username="bob@example.com",
            email="bob@example.com",
            password="OldPassword123!",
            first_name="Bob",
            last_name="Jones",
        )
        cls.user3 = User.objects.create_user(
            username="charlie@example.com",
            email="charlie@example.com",
            password="OldPassword123!",
            first_name="Charlie",
            last_name="Brown",
        )
        cls.unlinked_user = User.objects.create_user(
            username="nolink@example.com",
            email="nolink@example.com",
            password="OldPassword123!",
        )
        cls.superuser = User.objects.create_superuser(
            username="admin@example.com",
            email="admin@example.com",
            password="AdminPassword123!",
        )

        cls.alice = Player.objects.create(
            first_name="Alice", last_name="Smith", user=cls.user1
        )
        cls.bob = Player.objects.create(
            first_name="Bob", last_name="Jones", user=cls.user2
        )
        cls.charlie = Player.objects.create(
            first_name="Charlie", last_name="Brown", user=cls.user3
        )

        today = datetime.date.today()
        cls.season = Season.objects.create(
            name="2026 Round 1",
            start_date=today - datetime.timedelta(days=10),
            end_date=today + datetime.timedelta(days=20),
            season_round=1,
            is_draft=False,
        )
        cls.ladder = Ladder.objects.create(
            season=cls.season, division=1, ladder_type="First to 9"
        )
        League.objects.create(ladder=cls.ladder, player=cls.alice, sort_order=10)
        League.objects.create(ladder=cls.ladder, player=cls.bob, sort_order=20)
        League.objects.create(ladder=cls.ladder, player=cls.charlie, sort_order=30)

    def _auth_header(self, user):
        token, _ = create_access_token(user)
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def test_result_entry_context_and_unlinked_user(self):
        # Unlinked user returns has_active_ladder=False
        resp_unlinked = self.client.get(
            "/v1/ladder/results/entry/", **self._auth_header(self.unlinked_user)
        )
        self.assertEqual(resp_unlinked.status_code, 200)
        self.assertFalse(resp_unlinked.json()["has_active_ladder"])

        # Alice sees Bob and Charlie as unplayed
        resp = self.client.get(
            "/v1/ladder/results/entry/", **self._auth_header(self.user1)
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["has_active_ladder"])
        self.assertEqual(data["total_opponents"], 2)
        self.assertEqual([u["id"] for u in data["unplayed"]], [self.bob.id, self.charlie.id])

    def test_submit_edit_and_delete_results_and_permissions(self):
        headers = self._auth_header(self.user1)

        # 1. Submit won match vs Bob (9-4)
        sub_won = self.client.post(
            "/v1/ladder/results/entry/",
            data=json.dumps(
                {
                    "opponent_id": self.bob.id,
                    "outcome": "won",
                    "primary_score": 4,
                }
            ),
            content_type="application/json",
            **headers,
        )
        self.assertEqual(sub_won.status_code, 200)
        pair_key = sub_won.json()["pair_key"]

        # Verify reciprocal rows
        self.assertEqual(
            Result.objects.get(
                ladder=self.ladder, player=self.alice, opponent=self.bob
            ).result,
            9,
        )
        self.assertEqual(
            Result.objects.get(
                ladder=self.ladder, player=self.bob, opponent=self.alice
            ).result,
            4,
        )

        # 2. Submit incomplete time match vs Charlie (6-5)
        sub_time = self.client.post(
            "/v1/ladder/results/entry/",
            data=json.dumps(
                {
                    "opponent_id": self.charlie.id,
                    "outcome": "incomplete",
                    "incomplete_reason": "time",
                    "primary_score": 6,
                    "opponent_score": 5,
                }
            ),
            content_type="application/json",
            **headers,
        )
        self.assertEqual(sub_time.status_code, 200)
        time_pair = sub_time.json()["pair_key"]

        # 3. Non-participant Charlie cannot edit Alice vs Bob -> 403
        charlie_headers = self._auth_header(self.user3)
        forbid_edit = self.client.put(
            f"/v1/ladder/results/entry/{pair_key}/",
            data=json.dumps(
                {
                    "match_mode": "completed",
                    "winner_id": self.bob.id,
                    "losing_score": 2,
                }
            ),
            content_type="application/json",
            **charlie_headers,
        )
        self.assertEqual(forbid_edit.status_code, 403)

        # 4. Participant Alice edits Alice vs Bob to injury retirement (Bob wins 9-3)
        edit_inj = self.client.put(
            f"/v1/ladder/results/entry/{pair_key}/",
            data=json.dumps(
                {
                    "match_mode": "injury",
                    "winner_id": self.bob.id,
                    "losing_score": 3,
                }
            ),
            content_type="application/json",
            **headers,
        )
        self.assertEqual(edit_inj.status_code, 200)
        self.assertTrue(edit_inj.json()["changed"])

        r_alice = Result.objects.get(
            ladder=self.ladder, player=self.alice, opponent=self.bob
        )
        self.assertEqual(r_alice.result, 3)
        self.assertEqual(r_alice.incomplete_reason, Result.IncompleteReason.INJURY)

        # No-op edit returns changed=False
        noop_edit = self.client.put(
            f"/v1/ladder/results/entry/{pair_key}/",
            data=json.dumps(
                {
                    "match_mode": "injury",
                    "winner_id": self.bob.id,
                    "losing_score": 3,
                }
            ),
            content_type="application/json",
            **headers,
        )
        self.assertEqual(noop_edit.status_code, 200)
        self.assertFalse(noop_edit.json()["changed"])

        # 5. Non-participant cannot delete -> 403
        forbid_del = self.client.delete(
            f"/v1/ladder/results/entry/{pair_key}/", **charlie_headers
        )
        self.assertEqual(forbid_del.status_code, 403)

        # 6. Participant deletes incomplete match
        del_resp = self.client.delete(
            f"/v1/ladder/results/entry/{time_pair}/", **headers
        )
        self.assertEqual(del_resp.status_code, 200)
        self.assertFalse(
            Result.objects.filter(
                ladder=self.ladder, player=self.alice, opponent=self.charlie
            ).exists()
        )

    def test_closed_round_blocks_player_but_allows_admin(self):
        # Close season
        self.season.end_date = datetime.date.today() - datetime.timedelta(days=1)
        self.season.save(update_fields=["end_date"])

        resp = self.client.post(
            "/v1/ladder/results/entry/",
            data=json.dumps(
                {"opponent_id": self.bob.id, "outcome": "won", "primary_score": 6}
            ),
            content_type="application/json",
            **self._auth_header(self.user1),
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("closed", resp.json()["detail"].lower())

        # Non-superuser cannot hit admin submit -> 403
        year = self.season.start_date.year
        non_admin = self.client.post(
            f"/v1/ladder/results/admin/{year}/round/1/division/1/",
            data=json.dumps(
                {
                    "winner_id": self.alice.id,
                    "loser_id": self.bob.id,
                    "losing_score": 6,
                }
            ),
            content_type="application/json",
            **self._auth_header(self.user1),
        )
        self.assertEqual(non_admin.status_code, 403)

        # Superuser can submit even when round is closed
        admin_resp = self.client.post(
            f"/v1/ladder/results/admin/{year}/round/1/division/1/",
            data=json.dumps(
                {
                    "winner_id": self.alice.id,
                    "loser_id": self.bob.id,
                    "losing_score": 6,
                }
            ),
            content_type="application/json",
            **self._auth_header(self.superuser),
        )
        self.assertEqual(admin_resp.status_code, 200)

    def test_account_email_password_and_device_tokens(self):
        headers = self._auth_header(self.user1)

        # GET account
        acc_resp = self.client.get("/v1/account/", **headers)
        self.assertEqual(acc_resp.status_code, 200)
        self.assertEqual(acc_resp.json()["email"], "alice@example.com")
        self.assertEqual(acc_resp.json()["current_division"]["division"], 1)

        # Duplicate email rejected
        dup_email = self.client.patch(
            "/v1/account/email/",
            data=json.dumps({"email": "bob@example.com"}),
            content_type="application/json",
            **headers,
        )
        self.assertEqual(dup_email.status_code, 400)

        # Valid email update sends confirmation to both old & new
        ok_email = self.client.patch(
            "/v1/account/email/",
            data=json.dumps({"email": "alice.new@example.com"}),
            content_type="application/json",
            **headers,
        )
        self.assertEqual(ok_email.status_code, 200)
        self.assertEqual(ok_email.json()["email"], "alice.new@example.com")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].to, ["alice@example.com", "alice.new@example.com"]
        )

        # Device push token register & unregister
        reg_resp = self.client.post(
            "/v1/account/devices/",
            data=json.dumps(
                {
                    "expo_push_token": "ExponentPushToken[test123]",
                    "platform": "ios",
                }
            ),
            content_type="application/json",
            **headers,
        )
        self.assertEqual(reg_resp.status_code, 200)
        self.assertTrue(
            DevicePushToken.objects.filter(
                user=self.user1,
                expo_push_token="ExponentPushToken[test123]",
                is_active=True,
            ).exists()
        )

        unreg_resp = self.client.delete(
            "/v1/account/devices/",
            data=json.dumps({"expo_push_token": "ExponentPushToken[test123]"}),
            content_type="application/json",
            **headers,
        )
        self.assertEqual(unreg_resp.status_code, 200)
        self.assertFalse(
            DevicePushToken.objects.get(
                expo_push_token="ExponentPushToken[test123]"
            ).is_active
        )

        # Change password revokes active refresh tokens
        rt = RefreshToken.objects.create(
            user=self.user1,
            token_hash=hash_refresh_token("active-tok"),
            expires_at=datetime.datetime.now() + datetime.timedelta(days=5),
        )
        pw_resp = self.client.post(
            "/v1/account/password/",
            data=json.dumps(
                {
                    "old_password": "OldPassword123!",
                    "new_password": "NewStrongPassword789!",
                }
            ),
            content_type="application/json",
            **headers,
        )
        self.assertEqual(pw_resp.status_code, 200)
        rt.refresh_from_db()
        self.assertIsNotNone(rt.revoked_at)

    def test_account_subscriptions_exclude_closed_seasons(self):
        today = datetime.date.today()
        closed_season = Season.objects.create(
            name="2024 Round 1",
            start_date=today - datetime.timedelta(days=120),
            end_date=today - datetime.timedelta(days=5),
            season_round=1,
            is_draft=False,
        )
        closed_ladder = Ladder.objects.create(
            season=closed_season, division=1, ladder_type="First to 9"
        )
        LadderSubscription.objects.get_or_create(
            user=self.user1,
            ladder=closed_ladder,
            defaults={"subscribed_at": today - datetime.timedelta(days=90)},
        )
        LadderSubscription.objects.get_or_create(
            user=self.user1,
            ladder=self.ladder,
            defaults={"subscribed_at": today},
        )

        acc_resp = self.client.get(
            "/v1/account/", **self._auth_header(self.user1)
        )
        self.assertEqual(acc_resp.status_code, 200)
        subs = acc_resp.json()["subscriptions"]
        self.assertEqual(len(subs), 1)
        self.assertEqual(subs[0]["ladder_id"], self.ladder.id)
