import datetime
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from ladder.models import Ladder, League, Player, Season
from ladder.services.player import PlayerStatsService


class PlayerSearchTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="member", password="password123")
        self.season_old = Season.objects.create(
            name="2022 Round 1",
            start_date=datetime.date(2022, 1, 1),
            end_date=datetime.date(2022, 4, 1),
            season_round=1,
            is_draft=False,
        )
        self.season_recent = Season.objects.create(
            name="2026 Round 1",
            start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 4, 1),
            season_round=1,
            is_draft=False,
        )
        self.ladder_old = Ladder.objects.create(season=self.season_old, division=1)
        self.ladder_recent = Ladder.objects.create(season=self.season_recent, division=1)

        # Substring match created first (like Ahmad when searching "ad")
        self.p_ahmad = Player.objects.create(first_name="Ahmad", last_name="ZAHEDIEH")
        # Prefix matches
        self.p_adam_old = Player.objects.create(first_name="Adam", last_name="FRANTZIS")
        self.p_adam_recent = Player.objects.create(first_name="Adam", last_name="MCCARTHY")
        # Surname substring match
        self.p_gadgil = Player.objects.create(first_name="Shashi", last_name="GADGIL")

        League.objects.create(ladder=self.ladder_old, player=self.p_adam_old, sort_order=1)
        League.objects.create(ladder=self.ladder_recent, player=self.p_adam_recent, sort_order=1)

    def test_search_relevance_orders_prefix_and_recent_activity_first(self):
        results = PlayerStatsService.search_players(query="ad", authenticated=True)
        self.assertEqual(
            [p.id for p in results],
            [self.p_adam_recent.id, self.p_adam_old.id, self.p_ahmad.id, self.p_gadgil.id],
        )

    def test_autocomplete_respects_surname_chopping_and_privacy(self):
        anon_options = PlayerStatsService.autocomplete_players(query="ad", authenticated=False)
        self.assertEqual(
            [opt["label"] for opt in anon_options],
            ["Adam M.", "Adam F.", "Ahmad Z."],
        )
        self.assertEqual(anon_options[0]["subtext"], "1 round · active 2026")
        self.assertEqual(anon_options[1]["subtext"], "1 round · active 2022")
        self.assertEqual(anon_options[2]["subtext"], "")

        auth_options = PlayerStatsService.autocomplete_players(query="ad", authenticated=True)
        self.assertEqual(
            [opt["label"] for opt in auth_options],
            ["Adam MCCARTHY", "Adam FRANTZIS", "Ahmad ZAHEDIEH", "Shashi GADGIL"],
        )
        self.assertEqual(auth_options[0]["subtext"], "1 round · active 2026")

    def test_results_view_displays_chopped_or_full_names_by_auth_state(self):
        url = reverse("player_result") + "?player_name=ad"

        anon_resp = self.client.get(url)
        self.assertEqual(anon_resp.status_code, 200)
        self.assertContains(anon_resp, "Adam M.")
        self.assertNotContains(anon_resp, "Adam MCCARTHY")

        self.client.login(username="member", password="password123")
        auth_resp = self.client.get(url)
        self.assertEqual(auth_resp.status_code, 200)
        self.assertContains(auth_resp, "Adam MCCARTHY")
        self.assertContains(auth_resp, "Adam FRANTZIS")
