import datetime
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User, AnonymousUser
from django.urls import reverse

from ladder.models import Player, Season, Ladder, League, Result
from ladder.services.stats import ClubStatsService
from ladder.views import stats


class StatsServiceTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Clear out default data from migrations so our test environment is pristine
        Result.objects.all().delete()
        League.objects.all().delete()
        Ladder.objects.all().delete()
        Season.objects.all().delete()
        Player.objects.all().delete()

        # Create test users
        cls.user_auth = User.objects.create_user(username='auth_user', email='auth@example.com')

        # Create players
        cls.player1 = Player.objects.create(first_name='Alice', last_name='Smith')
        cls.player2 = Player.objects.create(first_name='Bob', last_name='Jones')
        cls.player3 = Player.objects.create(first_name='Charlie', last_name='Brown')
        cls.player4 = Player.objects.create(first_name='Diana', last_name='Prince')

        # Create two published seasons and one draft season
        today = datetime.date.today()
        cls.season_old = Season.objects.create(
            name='2020 Round 1',
            start_date=today - datetime.timedelta(days=700),
            end_date=today - datetime.timedelta(days=640),
            season_round=1,
            is_draft=False,
        )
        cls.season_recent = Season.objects.create(
            name='2026 Round 1',
            start_date=today - datetime.timedelta(days=60),
            end_date=today - datetime.timedelta(days=10),
            season_round=1,
            is_draft=False,
        )
        cls.season_draft = Season.objects.create(
            name='2026 Round 2 (Draft)',
            start_date=today + datetime.timedelta(days=10),
            end_date=today + datetime.timedelta(days=70),
            season_round=2,
            is_draft=True,
        )

        # Ladders for season_recent
        cls.ladder_div1 = Ladder.objects.create(season=cls.season_recent, division=1, ladder_type='A')
        cls.ladder_div2 = Ladder.objects.create(season=cls.season_recent, division=2, ladder_type='A')

        # Ladder for season_old
        cls.ladder_old_div1 = Ladder.objects.create(season=cls.season_old, division=1, ladder_type='A')

        # Leagues in recent season
        # Div 1: player1, player2
        cls.league_r_p1 = League.objects.create(ladder=cls.ladder_div1, player=cls.player1, sort_order=1)
        cls.league_r_p2 = League.objects.create(ladder=cls.ladder_div1, player=cls.player2, sort_order=2)
        # Div 2: player3, player4
        cls.league_r_p3 = League.objects.create(ladder=cls.ladder_div2, player=cls.player3, sort_order=1)
        cls.league_r_p4 = League.objects.create(ladder=cls.ladder_div2, player=cls.player4, sort_order=2)

        # Leagues in old season
        cls.league_o_p1 = League.objects.create(ladder=cls.ladder_old_div1, player=cls.player1, sort_order=1)
        cls.league_o_p2 = League.objects.create(ladder=cls.ladder_old_div1, player=cls.player2, sort_order=2)

        # Matches in recent season:
        # player1 beats player2: 9 - 4
        Result.objects.create(
            ladder=cls.ladder_div1, player=cls.player1, opponent=cls.player2,
            result=9, date_added=cls.season_recent.start_date + datetime.timedelta(days=5), inaccurate_flag=False
        )
        Result.objects.create(
            ladder=cls.ladder_div1, player=cls.player2, opponent=cls.player1,
            result=4, date_added=cls.season_recent.start_date + datetime.timedelta(days=5), inaccurate_flag=False
        )

        # player3 beats player4: 9 - 7
        Result.objects.create(
            ladder=cls.ladder_div2, player=cls.player3, opponent=cls.player4,
            result=9, date_added=cls.season_recent.start_date + datetime.timedelta(days=6), inaccurate_flag=False
        )
        Result.objects.create(
            ladder=cls.ladder_div2, player=cls.player4, opponent=cls.player3,
            result=7, date_added=cls.season_recent.start_date + datetime.timedelta(days=6), inaccurate_flag=False
        )

        # Matches in old season:
        # player2 beats player1: 9 - 6
        Result.objects.create(
            ladder=cls.ladder_old_div1, player=cls.player2, opponent=cls.player1,
            result=9, date_added=cls.season_old.start_date + datetime.timedelta(days=10), inaccurate_flag=False
        )
        Result.objects.create(
            ladder=cls.ladder_old_div1, player=cls.player1, opponent=cls.player2,
            result=6, date_added=cls.season_old.start_date + datetime.timedelta(days=10), inaccurate_flag=False
        )

    def test_resolve_filter_all_time(self):
        all_seasons = list(Season.objects.filter(is_draft=False).order_by('-start_date'))
        res = ClubStatsService.resolve_filter(all_seasons, period='all')
        self.assertEqual(res['filter_type'], 'period')
        self.assertEqual(res['period'], 'all')
        self.assertEqual(res['filter_label'], 'All-Time')
        self.assertEqual(len(res['seasons']), 2)

    def test_resolve_filter_by_year(self):
        all_seasons = list(Season.objects.filter(is_draft=False).order_by('-start_date'))
        year = self.season_old.start_date.year
        res = ClubStatsService.resolve_filter(all_seasons, year=year)
        self.assertEqual(res['filter_type'], 'year')
        self.assertEqual(res['selected_year'], year)
        self.assertEqual(len(res['seasons']), 1)
        self.assertEqual(res['seasons'][0].id, self.season_old.id)

    def test_resolve_filter_by_season(self):
        all_seasons = list(Season.objects.filter(is_draft=False).order_by('-start_date'))
        res = ClubStatsService.resolve_filter(all_seasons, season_id=self.season_recent.id)
        self.assertEqual(res['filter_type'], 'season')
        self.assertEqual(res['selected_season_id'], self.season_recent.id)
        self.assertEqual(len(res['seasons']), 1)

    def test_name_formatting_privacy(self):
        anon_name = ClubStatsService._format_player_name('Alice', 'Smith', authenticated=False)
        auth_name = ClubStatsService._format_player_name('Alice', 'Smith', authenticated=True)
        self.assertEqual(anon_name, 'Alice S.')
        self.assertEqual(auth_name, 'Alice Smith')

    def test_get_club_stats_leaderboards(self):
        stats_data = ClubStatsService.get_club_stats(period='all', authenticated=True)
        summary = stats_data['summary']
        leaderboards = stats_data['leaderboards']

        # Verify summary
        self.assertEqual(summary['seasons_count'], 2)
        self.assertEqual(summary['divisions_count'], 3)
        self.assertEqual(summary['matches_played'], 3)  # 6 result rows / 2

        # 1. Most Matches Won: Alice (1) and Bob (1) and Charlie (1)
        most_won = leaderboards['most_won']
        self.assertTrue(len(most_won) >= 3)
        winners = {row['player_id'] for row in most_won}
        self.assertIn(self.player1.id, winners)
        self.assertIn(self.player2.id, winners)
        self.assertIn(self.player3.id, winners)

        # 2. Most Matches Played: Alice (2), Bob (2), Charlie (1), Diana (1)
        most_played = leaderboards['most_played']
        self.assertEqual(most_played[0]['player_id'], self.player1.id)
        self.assertEqual(most_played[0]['played'], 2)

        # 3. Most Total Points:
        # Alice: Win (12) + Loss (6+1 = 7) = 19 pts
        # Bob: Win (12) + Loss (4+1 = 5) = 17 pts
        # Charlie: Win (12) = 12 pts
        # Diana: Loss (7+1 = 8) = 8 pts
        most_points = leaderboards['most_points']
        self.assertEqual(most_points[0]['player_id'], self.player1.id)
        self.assertEqual(most_points[0]['total_points'], 19)
        self.assertEqual(most_points[1]['player_id'], self.player2.id)
        self.assertEqual(most_points[1]['total_points'], 17)

        # 4. Most Division Titles:
        # In recent season:
        # Div 1: Alice has 12 pts (winner), Bob has 5 pts
        # Div 2: Charlie has 12 pts (winner), Diana has 8 pts
        # In old season:
        # Div 1: Bob has 12 pts (winner), Alice has 7 pts
        most_titles = leaderboards['most_titles']
        titles_by_player = {row['player_id']: row for row in most_titles}
        self.assertIn(self.player1.id, titles_by_player)
        self.assertIn(self.player2.id, titles_by_player)
        self.assertIn(self.player3.id, titles_by_player)

        # Alice won Div 1 once
        self.assertEqual(titles_by_player[self.player1.id]['division_titles'], 1)
        self.assertEqual(titles_by_player[self.player1.id]['div1_titles'], 1)
        # Charlie won Div 2 once
        self.assertEqual(titles_by_player[self.player3.id]['division_titles'], 1)
        self.assertEqual(titles_by_player[self.player3.id]['div1_titles'], 0)
        # Check badge formatting
        charlie_badges = titles_by_player[self.player3.id]['divisions_won_badges']
        self.assertEqual(len(charlie_badges), 1)
        self.assertEqual(charlie_badges[0]['label'], 'Div 2')
        self.assertFalse(charlie_badges[0]['is_div1'])

        # 5. Highest Completion %
        # Alice played 2 / scheduled 2 = 100%
        # Bob played 2 / scheduled 2 = 100%
        highest_completion = leaderboards['highest_completion']
        self.assertTrue(any(row['player_id'] == self.player1.id for row in highest_completion))

        # 6. Top Rivalries: Alice vs Bob played 2 matches (1 win each)
        top_rivalries = leaderboards['top_rivalries']
        self.assertEqual(len(top_rivalries), 1)
        rivalry = top_rivalries[0]
        self.assertEqual(rivalry['matches_played'], 2)
        self.assertEqual(set([rivalry['player_a_id'], rivalry['player_b_id']]), {self.player1.id, self.player2.id})
        self.assertEqual(rivalry['player_a_wins'], 1)
        self.assertEqual(rivalry['player_b_wins'], 1)

        # 7. Best Centile:
        # Alice won Div 1 in recent season (rank 1 of 4) -> 100%
        # Bob won Div 1 in old season (rank 1 of 2) -> 100%
        best_centile = leaderboards['best_centile']
        centile_by_player = {row['player_id']: row for row in best_centile}
        self.assertEqual(centile_by_player[self.player1.id]['best_centile'], 100)
        self.assertEqual(centile_by_player[self.player2.id]['best_centile'], 100)


class StatsViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.factory = RequestFactory()
        cls.user = User.objects.create_user(username='testuser', password='password')
        today = datetime.date.today()
        cls.season = Season.objects.create(
            name='2026 Round 1',
            start_date=today - datetime.timedelta(days=30),
            end_date=today - datetime.timedelta(days=1),
            season_round=1,
            is_draft=False,
        )

    def test_stats_view_anonymous(self):
        response = self.client.get(reverse('stats'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'ladder/stats/index.html')
        self.assertIn('leaderboards', response.context)
        self.assertIn('summary', response.context)

    def test_stats_view_authenticated(self):
        self.client.login(username='testuser', password='password')
        response = self.client.get(reverse('stats'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('leaderboards', response.context)

    def test_stats_view_with_filters(self):
        # Period filter
        response = self.client.get(reverse('stats') + '?period=5y')
        self.assertEqual(response.status_code, 200)

        # Year filter
        year = self.season.start_date.year
        response = self.client.get(reverse('stats') + f'?year={year}')
        self.assertEqual(response.status_code, 200)

        # Season filter
        response = self.client.get(reverse('stats') + f'?season={self.season.id}')
        self.assertEqual(response.status_code, 200)
