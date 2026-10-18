import datetime
from django.test import TestCase
from django.urls import reverse

from ladder.models import Ladder, League, Player, Result, Season
from ladder.services.player import PlayerStatsService


class PlayerStatsServiceTest(TestCase):
    def setUp(self):
        self.season = Season.objects.create(
            name="2026 Round 1",
            start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 3, 31),
            season_round=1,
            is_draft=False,
        )
        self.ladder = Ladder.objects.create(
            season=self.season,
            division=1,
            ladder_type="Main",
        )
        self.p1 = Player.objects.create(first_name="Alice", last_name="Anderson")
        self.p2 = Player.objects.create(first_name="Bob", last_name="Brown")
        self.p3 = Player.objects.create(first_name="Charlie", last_name="Clark")

        League.objects.create(ladder=self.ladder, player=self.p1, sort_order=1)
        League.objects.create(ladder=self.ladder, player=self.p2, sort_order=2)
        League.objects.create(ladder=self.ladder, player=self.p3, sort_order=3)

        # Match 1: Alice beats Bob 9-7 (close match)
        Result.objects.create(
            ladder=self.ladder,
            player=self.p1,
            opponent=self.p2,
            result=9,
            date_added=datetime.date(2026, 2, 1),
            inaccurate_flag=False,
        )
        Result.objects.create(
            ladder=self.ladder,
            player=self.p2,
            opponent=self.p1,
            result=7,
            date_added=datetime.date(2026, 2, 1),
            inaccurate_flag=False,
        )

        # Match 2: Alice beats Charlie 9-0 (bagel / dominant win)
        Result.objects.create(
            ladder=self.ladder,
            player=self.p1,
            opponent=self.p3,
            result=9,
            date_added=datetime.date(2026, 2, 10),
            inaccurate_flag=False,
        )
        Result.objects.create(
            ladder=self.ladder,
            player=self.p3,
            opponent=self.p1,
            result=0,
            date_added=datetime.date(2026, 2, 10),
            inaccurate_flag=False,
        )

    def test_get_player_profile_stats_and_insights(self):
        ctx = PlayerStatsService.get_player_profile(self.p1, authenticated=False)
        stats = ctx["player_stats"]
        insights = ctx["insights"]
        head = ctx["head"]

        self.assertEqual(stats["played"], 2)
        self.assertEqual(stats["won"], 2)
        self.assertEqual(stats["lost"], 0)
        self.assertEqual(stats["total_points"], 24)
        self.assertEqual(stats["unique_opponents"], 2)

        self.assertTrue(insights["has_matches"])
        self.assertEqual(insights["longest_win_streak"], 2)
        self.assertEqual(insights["clutch_played"], 1)
        self.assertEqual(insights["clutch_won"], 1)
        self.assertEqual(insights["bagels_won"], 1)
        self.assertEqual(insights["dominant_wins"], 1)
        self.assertEqual(insights["full_completion_rounds"], 1)

        # Check head-to-head Won/Played records
        by_opp = {h["opponent"]: h for h in head}
        self.assertEqual(by_opp[self.p2.id]["won_played_display"], "1/1")
        self.assertEqual(by_opp[self.p2.id]["opponent_name"], "Bob B.")

    def test_get_head_to_head_and_modal_view(self):
        h2h = PlayerStatsService.get_head_to_head(self.p1, self.p2, authenticated=False)
        self.assertEqual(h2h["stats"]["played"], 1)
        self.assertEqual(h2h["stats"]["won"], 1)
        self.assertEqual(h2h["stats"]["lost"], 0)
        self.assertEqual(h2h["stats"]["player_games"], 9)
        self.assertEqual(h2h["stats"]["opponent_games"], 7)
        self.assertEqual(h2h["stats"]["close_matches"], 1)

        # Modal request should render partial without base html nav
        url = reverse("head_to_head", args=(self.p1.id, self.p2.id))
        resp_modal = self.client.get(url + "?modal=1")
        self.assertEqual(resp_modal.status_code, 200)
        self.assertContains(resp_modal, "h2h-detail-content")
        self.assertNotContains(resp_modal, "<html")

        # Standard request should render full page
        resp_full = self.client.get(url)
        self.assertEqual(resp_full.status_code, 200)
        self.assertContains(resp_full, "<html")
        self.assertContains(resp_full, "h2h-detail-content")

    def test_player_history_view_responsive_labels_and_lightbox(self):
        url = reverse("player_history", args=(self.p1.id,))
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        # Mobile short label and desktop full label
        self.assertContains(resp, "2026 R1 &middot; Div 1")
        self.assertContains(resp, "2026 Round 1 &middot; Division 1")
        # Lightbox modal container and Won / Played header
        self.assertContains(resp, 'id="h2hLightboxModal"')
        self.assertContains(resp, "Won / Played")
