import datetime
import json

import jwt
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from api.auth import (
    REFRESH_COOKIE_NAME,
    _signing_key,
    create_access_token,
    hash_refresh_token,
)
from api.models import RefreshToken
from ladder.models import Ladder, League, Player, Result, Season


class ApiAuthTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Result.objects.all().delete()
        League.objects.all().delete()
        Ladder.objects.all().delete()
        Season.objects.all().delete()
        Player.objects.all().delete()

        cls.user = User.objects.create_user(
            username="alice_user",
            email="alice@example.com",
            password="OldPassword123!",
            first_name="Alice",
            last_name="Smith",
        )
        organiser_group, _ = Group.objects.get_or_create(name="player")
        cls.user.groups.add(organiser_group)

        cls.player = Player.objects.create(
            first_name="Alice", last_name="Smith", user=cls.user
        )
        cls.player2 = Player.objects.create(first_name="Bob", last_name="Jones")

        today = datetime.date.today()
        cls.season = Season.objects.create(
            name="2026 Round 1",
            start_date=today - datetime.timedelta(days=10),
            end_date=today + datetime.timedelta(days=30),
            season_round=1,
            is_draft=False,
        )
        cls.ladder = Ladder.objects.create(
            season=cls.season, division=1, ladder_type="First to 9"
        )
        League.objects.create(ladder=cls.ladder, player=cls.player, sort_order=10)
        League.objects.create(ladder=cls.ladder, player=cls.player2, sort_order=20)

    def test_login_with_email_and_username_and_me(self):
        # Login by email (case-insensitive) even when username != email
        resp = self.client.post(
            "/v1/auth/login",
            data=json.dumps(
                {
                    "email": "ALICE@example.com",
                    "password": "OldPassword123!",
                    "device_label": "iPhone Expo Go",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["token_type"], "Bearer")
        self.assertTrue(body["access_token"])
        self.assertTrue(body["refresh_token"])
        self.assertEqual(body["user"]["player_id"], self.player.id)
        self.assertEqual(body["user"]["player_name"], "Alice Smith")
        self.assertEqual(body["user"]["active_division"]["division"], 1)
        self.assertIn("player", body["user"]["roles"])

        # Login by legacy username also works
        resp_u = self.client.post(
            "/v1/auth/login",
            data=json.dumps({"email": "alice_user", "password": "OldPassword123!"}),
            content_type="application/json",
        )
        self.assertEqual(resp_u.status_code, 200)

        # Bad password -> 401
        bad_resp = self.client.post(
            "/v1/auth/login",
            data=json.dumps({"email": "alice@example.com", "password": "wrong"}),
            content_type="application/json",
        )
        self.assertEqual(bad_resp.status_code, 401)

        # /me requires valid Bearer token
        unauth_me = self.client.get("/v1/auth/me")
        self.assertEqual(unauth_me.status_code, 401)

        auth_me = self.client.get(
            "/v1/auth/me",
            HTTP_AUTHORIZATION=f"Bearer {body['access_token']}",
        )
        self.assertEqual(auth_me.status_code, 200)
        self.assertEqual(auth_me.json()["email"], "alice@example.com")

    def test_native_refresh_rotation_and_logout_revocation(self):
        login_resp = self.client.post(
            "/v1/auth/login",
            data=json.dumps({"email": "alice@example.com", "password": "OldPassword123!"}),
            content_type="application/json",
        )
        old_refresh = login_resp.json()["refresh_token"]

        # Rotate refresh token
        ref_resp = self.client.post(
            "/v1/auth/refresh",
            data=json.dumps({"refresh_token": old_refresh}),
            content_type="application/json",
        )
        self.assertEqual(ref_resp.status_code, 200)
        new_refresh = ref_resp.json()["refresh_token"]
        self.assertTrue(new_refresh)
        self.assertNotEqual(new_refresh, old_refresh)

        # Reusing old refresh token fails
        reuse_resp = self.client.post(
            "/v1/auth/refresh",
            data=json.dumps({"refresh_token": old_refresh}),
            content_type="application/json",
        )
        self.assertEqual(reuse_resp.status_code, 401)

        # Logout revokes current refresh token
        logout_resp = self.client.post(
            "/v1/auth/logout",
            data=json.dumps({"refresh_token": new_refresh}),
            content_type="application/json",
        )
        self.assertEqual(logout_resp.status_code, 200)

        after_logout = self.client.post(
            "/v1/auth/refresh",
            data=json.dumps({"refresh_token": new_refresh}),
            content_type="application/json",
        )
        self.assertEqual(after_logout.status_code, 401)

    def test_web_client_uses_httponly_cookie_for_refresh_and_logout(self):
        login_resp = self.client.post(
            "/v1/auth/login",
            data=json.dumps({"email": "alice@example.com", "password": "OldPassword123!"}),
            content_type="application/json",
            HTTP_X_CLIENT_PLATFORM="web",
        )
        self.assertEqual(login_resp.status_code, 200)
        self.assertIsNone(login_resp.json()["refresh_token"])
        self.assertIn(REFRESH_COOKIE_NAME, login_resp.cookies)
        cookie = login_resp.cookies[REFRESH_COOKIE_NAME]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["path"], "/v1/auth/")

        # Empty POST body refresh uses cookie
        ref_resp = self.client.post(
            "/v1/auth/refresh",
            HTTP_X_CLIENT_PLATFORM="web",
        )
        self.assertEqual(ref_resp.status_code, 200)
        self.assertIsNone(ref_resp.json()["refresh_token"])
        self.assertIn(REFRESH_COOKIE_NAME, ref_resp.cookies)

        # Empty POST body logout revokes and clears cookie
        logout_resp = self.client.post(
            "/v1/auth/logout",
            HTTP_X_CLIENT_PLATFORM="web",
        )
        self.assertEqual(logout_resp.status_code, 200)
        self.assertEqual(logout_resp.cookies[REFRESH_COOKIE_NAME].value, "")

        # Refresh after logout fails
        post_logout_ref = self.client.post(
            "/v1/auth/refresh",
            HTTP_X_CLIENT_PLATFORM="web",
        )
        self.assertEqual(post_logout_ref.status_code, 401)

    def test_optional_jwt_auth_never_downgrades_expired_or_invalid_bearer(self):
        # 1. No Authorization header -> 200 with abbreviated surnames
        anon_resp = self.client.get("/v1/players/search/?q=Bob")
        self.assertEqual(anon_resp.status_code, 200)
        self.assertEqual(anon_resp.json()["options"][0]["label"], "Bob J.")

        # 2. Valid Bearer -> 200 with full surnames
        access_token, _ = create_access_token(self.user)
        auth_resp = self.client.get(
            "/v1/players/search/?q=Bob",
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )
        self.assertEqual(auth_resp.status_code, 200)
        self.assertEqual(auth_resp.json()["options"][0]["label"], "Bob Jones")

        # 3. Expired Bearer -> 401 Unauthorized (NOT silent fallback to 200)
        expired_payload = {
            "sub": str(self.user.id),
            "type": "access",
            "iat": 1000,
            "exp": 1001,
        }
        expired_token = jwt.encode(
            expired_payload, _signing_key(), algorithm="HS256"
        )
        exp_resp = self.client.get(
            "/v1/players/search/?q=Bob",
            HTTP_AUTHORIZATION=f"Bearer {expired_token}",
        )
        self.assertEqual(exp_resp.status_code, 401)

        # 4. Malformed Bearer on overview -> 401 Unauthorized
        bad_overview = self.client.get(
            "/v1/ladder/seasons/current/overview",
            HTTP_AUTHORIZATION="Bearer not-a-jwt",
        )
        self.assertEqual(bad_overview.status_code, 401)

    def test_password_reset_request_and_confirm_revokes_tokens(self):
        _, refresh_rec = (
            "raw",
            RefreshToken.objects.create(
                user=self.user,
                token_hash=hash_refresh_token("sample-token"),
                expires_at=datetime.datetime.now() + datetime.timedelta(days=5),
            ),
        )

        # Existing email sends mail and returns generic 200
        req_resp = self.client.post(
            "/v1/auth/password-reset",
            data=json.dumps({"email": "alice@example.com"}),
            content_type="application/json",
        )
        self.assertEqual(req_resp.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

        # Non-existing email also returns generic 200
        unknown_resp = self.client.post(
            "/v1/auth/password-reset",
            data=json.dumps({"email": "nobody@example.com"}),
            content_type="application/json",
        )
        self.assertEqual(unknown_resp.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

        # Confirm password reset
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        confirm_resp = self.client.post(
            "/v1/auth/password-reset/confirm",
            data=json.dumps(
                {
                    "uid": uid,
                    "token": token,
                    "new_password": "BrandNewPassword456!",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(confirm_resp.status_code, 200)

        refresh_rec.refresh_from_db()
        self.assertIsNotNone(refresh_rec.revoked_at)

        login_new = self.client.post(
            "/v1/auth/login",
            data=json.dumps(
                {"email": "alice@example.com", "password": "BrandNewPassword456!"}
            ),
            content_type="application/json",
        )
        self.assertEqual(login_new.status_code, 200)
