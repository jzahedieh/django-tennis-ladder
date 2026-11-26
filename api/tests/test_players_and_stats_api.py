import datetime

from django.contrib.auth.models import User
from django.test import TestCase

from api.auth import create_access_token
from ladder.models import Ladder, League, Player, Result, Season


class PlayersAndStatsApiTests(TestCase):
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
        cls.alice = Player.objects.create(
            first_name="Alice", last_name="Smith", user=cls.user
        )
        cls.bob = Player.objects.create(first_name="Bob", last_name="Jones")
        cls.fresh = Player.objects.create(first_name="Fresh", last_name="Newcomer")

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
        League.objects.create(ladder=cls.ladder, player=cls.alice, sort_order=10)
        League.objects.create(ladder=cls.ladder, player=cls.bob, sort_order=20)

        Result.objects.create(
            ladder=cls.ladder,
            player=cls.alice,
            opponent=cls.bob,
            result=9,
            date_added=today,
        )
        Result.objects.create(
            ladder=cls.ladder,
            player=cls.bob,
            opponent=cls.alice,
            result=7,
            date_added=today,
        )

    def test_player_search_enumeration_protection_and_min_length(self):
        # < 2 chars returns empty
        short = self.client.get("/v1/players/search/?q=A")
        self.assertEqual(short.status_code, 200)
        self.assertEqual(short.json()["options"], [])

        # Anonymous cannot enumerate full surname
        anon_surname = self.client.get("/v1/players/search/?q=Jones")
        self.assertEqual(anon_surname.status_code, 200)
        self.assertEqual(anon_surname.json()["options"], [])

        # Authenticated can search full surname
        token, _ = create_access_token(self.user)
        auth_surname = self.client.get(
            "/v1/players/search/?q=Jones",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(auth_surname.status_code, 200)
        self.assertEqual(len(auth_surname.json()["options"]), 1)
        self.assertEqual(auth_surname.json()["options"][0]["label"], "Bob Jones")

    def test_player_profile_including_unplayed_player(self):
        # Fresh player with 0 matches still serializes cleanly
        fresh_resp = self.client.get(f"/v1/players/{self.fresh.id}/")
        self.assertEqual(fresh_resp.status_code, 200)
        fresh_data = fresh_resp.json()
        self.assertEqual(fresh_data["player_name"], "Fresh N.")
        self.assertEqual(fresh_data["stats"]["played"], "-")
        self.assertEqual(fresh_data["stats"]["completion_rate"], "- %")
        self.assertFalse(fresh_data["insights"]["has_matches"])

        # Authenticated view of Alice shows full rival names and match insights
        token, _ = create_access_token(self.user)
        alice_resp = self.client.get(
            f"/v1/players/{self.alice.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(alice_resp.status_code, 200)
        alice_data = alice_resp.json()
        self.assertTrue(alice_data["is_authenticated_view"])
        self.assertEqual(alice_data["player_name"], "Alice Smith")
        self.assertEqual(alice_data["stats"]["won"], 1)
        self.assertEqual(alice_data["head_to_head"][0]["opponent_name"], "Bob Jones")
        self.assertEqual(len(alice_data["season_history"]), 1)

        # Missing player -> 404
        self.assertEqual(self.client.get("/v1/players/999999/").status_code, 404)

    def test_head_to_head_endpoint(self):
        anon_h2h = self.client.get(f"/v1/players/{self.alice.id}/vs/{self.bob.id}/")
        self.assertEqual(anon_h2h.status_code, 200)
        data = anon_h2h.json()
        self.assertEqual(data["player_name"], "Alice S.")
        self.assertEqual(data["opponent_name"], "Bob J.")
        self.assertEqual(data["stats"]["won"], 1)
        self.assertEqual(data["stats"]["close_matches"], 1)
        self.assertEqual(data["matches"][0]["score_display"], "9 – 7")

    def test_club_stats_endpoint(self):
        resp = self.client.get("/v1/ladder/stats/?period=all")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["summary"]["matches_played"], 1)
        self.assertEqual(data["leaderboards"]["most_won"][0]["player_name"], "Alice S.")

        token, _ = create_access_token(self.user)
        auth_resp = self.client.get(
            f"/v1/ladder/stats/?season_id={self.season.id}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(auth_resp.status_code, 200)
        auth_data = auth_resp.json()
        self.assertEqual(
            auth_data["leaderboards"]["most_won"][0]["player_name"], "Alice Smith"
        )
