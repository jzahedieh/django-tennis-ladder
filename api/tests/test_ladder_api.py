import datetime

from django.contrib.auth.models import User
from django.test import TestCase

from api.auth import create_access_token
from ladder.models import Ladder, LadderSubscription, League, Player, Result, Season


class LadderApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Result.objects.all().delete()
        League.objects.all().delete()
        Ladder.objects.all().delete()
        Season.objects.all().delete()
        Player.objects.all().delete()

        cls.user = User.objects.create_user(
            username="p1@example.com", email="p1@example.com", password="Password123!"
        )
        cls.superuser = User.objects.create_superuser(
            username="admin@example.com",
            email="admin@example.com",
            password="Password123!",
        )

        cls.player1 = Player.objects.create(
            first_name="Alice", last_name="Smith", user=cls.user
        )
        cls.player2 = Player.objects.create(first_name="Bob", last_name="Jones")
        cls.player3 = Player.objects.create(first_name="Charlie", last_name="Brown")

        today = datetime.date.today()
        cls.season_old = Season.objects.create(
            name="2024 Round 1",
            start_date=datetime.date(2024, 1, 10),
            end_date=datetime.date(2024, 3, 20),
            season_round=1,
            is_draft=False,
        )
        cls.season_current = Season.objects.create(
            name="2026 Round 1",
            start_date=today - datetime.timedelta(days=15),
            end_date=today + datetime.timedelta(days=45),
            season_round=1,
            is_draft=False,
        )
        cls.season_draft = Season.objects.create(
            name="2026 Round 2 Draft",
            start_date=today + datetime.timedelta(days=50),
            end_date=today + datetime.timedelta(days=100),
            season_round=2,
            is_draft=True,
        )

        cls.ladder_c1 = Ladder.objects.create(
            season=cls.season_current, division=1, ladder_type="First to 9"
        )
        cls.ladder_c2 = Ladder.objects.create(
            season=cls.season_current, division=2, ladder_type="First to 9"
        )
        cls.ladder_o1 = Ladder.objects.create(
            season=cls.season_old, division=1, ladder_type="First to 9"
        )
        cls.ladder_draft = Ladder.objects.create(
            season=cls.season_draft, division=1, ladder_type="First to 9"
        )

        League.objects.create(ladder=cls.ladder_c1, player=cls.player1, sort_order=10)
        League.objects.create(ladder=cls.ladder_c1, player=cls.player2, sort_order=20)
        League.objects.create(ladder=cls.ladder_c1, player=cls.player3, sort_order=30)
        League.objects.create(ladder=cls.ladder_c2, player=cls.player2, sort_order=10)
        League.objects.create(ladder=cls.ladder_c2, player=cls.player3, sort_order=20)
        League.objects.create(ladder=cls.ladder_o1, player=cls.player1, sort_order=10)
        League.objects.create(ladder=cls.ladder_o1, player=cls.player2, sort_order=20)

        Result.objects.create(
            ladder=cls.ladder_c1,
            player=cls.player1,
            opponent=cls.player2,
            result=9,
            date_added=today - datetime.timedelta(days=2),
        )
        Result.objects.create(
            ladder=cls.ladder_c1,
            player=cls.player2,
            opponent=cls.player1,
            result=5,
            date_added=today - datetime.timedelta(days=2),
        )

    def test_current_overview_anonymous_vs_authenticated(self):
        anon_resp = self.client.get("/v1/ladder/seasons/current/overview")
        self.assertEqual(anon_resp.status_code, 200)
        anon_data = anon_resp.json()
        self.assertEqual(anon_data["season"]["id"], self.season_current.id)
        self.assertIsNone(anon_data["my_division"])
        self.assertEqual(anon_data["leaders"][0]["player"], "Alice S.")
        self.assertEqual(anon_data["recent_results"][0]["winner_name"], "Alice S.")

        token, _ = create_access_token(self.user)
        auth_resp = self.client.get(
            "/v1/ladder/seasons/current/overview",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(auth_resp.status_code, 200)
        auth_data = auth_resp.json()
        self.assertEqual(auth_data["leaders"][0]["player"], "Alice Smith")
        self.assertIsNotNone(auth_data["my_division"])
        self.assertEqual(auth_data["my_division"]["division"], 1)
        self.assertEqual(auth_data["my_division"]["total_points"], 12)
        self.assertEqual(auth_data["my_division"]["rank_in_division"], 1)

    def test_seasons_archive_and_draft_visibility(self):
        list_resp = self.client.get("/v1/ladder/seasons/")
        self.assertEqual(list_resp.status_code, 200)
        data = list_resp.json()
        self.assertEqual(len(data["seasons"]), 2)
        self.assertEqual(data["seasons"][0]["id"], self.season_current.id)
        self.assertTrue(data["seasons"][0]["is_latest"])

        # Draft season hidden from anonymous/regular users
        draft_year = self.season_draft.start_date.year
        anon_draft = self.client.get(f"/v1/ladder/seasons/{draft_year}/round/2/")
        self.assertEqual(anon_draft.status_code, 404)

        user_token, _ = create_access_token(self.user)
        user_draft = self.client.get(
            f"/v1/ladder/seasons/{draft_year}/round/2/",
            HTTP_AUTHORIZATION=f"Bearer {user_token}",
        )
        self.assertEqual(user_draft.status_code, 404)

        # Visible to superuser
        admin_token, _ = create_access_token(self.superuser)
        admin_draft = self.client.get(
            f"/v1/ladder/seasons/{draft_year}/round/2/",
            HTTP_AUTHORIZATION=f"Bearer {admin_token}",
        )
        self.assertEqual(admin_draft.status_code, 200)

        # Published season detail includes both divisions
        curr_year = self.season_current.start_date.year
        season_resp = self.client.get(f"/v1/ladder/seasons/{curr_year}/round/1/")
        self.assertEqual(season_resp.status_code, 200)
        self.assertEqual(len(season_resp.json()["divisions"]), 2)

    def test_division_detail_and_subscription_toggle(self):
        curr_year = self.season_current.start_date.year
        url = f"/v1/ladder/seasons/{curr_year}/round/1/division/1/"
        sub_url = f"{url}subscription/"

        anon_resp = self.client.get(url)
        self.assertEqual(anon_resp.status_code, 200)
        anon_data = anon_resp.json()
        self.assertFalse(anon_data["subscribed"])
        self.assertFalse(anon_data["has_prev_division"])
        self.assertTrue(anon_data["has_next_division"])
        self.assertEqual(anon_data["grid"]["rows"][0]["player_name"], "Alice S.")
        self.assertEqual(anon_data["stats"]["leader"]["player_name"], "Alice S.")

        # Unauthenticated subscription toggle -> 401
        self.assertEqual(self.client.post(sub_url).status_code, 401)

        # League signal auto-subscribed user; first toggle unsubscribes, second re-subscribes
        token, _ = create_access_token(self.user)
        auth_div = self.client.get(url, HTTP_AUTHORIZATION=f"Bearer {token}").json()
        self.assertTrue(auth_div["subscribed"])

        unsub = self.client.post(sub_url, HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(unsub.status_code, 200)
        self.assertFalse(unsub.json()["subscribed"])
        self.assertFalse(
            LadderSubscription.objects.filter(
                user=self.user, ladder=self.ladder_c1
            ).exists()
        )

        resub = self.client.post(sub_url, HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(resub.status_code, 200)
        self.assertTrue(resub.json()["subscribed"])
        self.assertTrue(
            LadderSubscription.objects.filter(
                user=self.user, ladder=self.ladder_c1
            ).exists()
        )
