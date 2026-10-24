import datetime
from django.contrib.auth.models import User, AnonymousUser
from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.utils.timezone import now

from ladder.models import Ladder, League, Player, Result, Season
from ladder.views import index


class HomepageRecentResultsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        Result.objects.all().delete()
        League.objects.all().delete()
        Ladder.objects.all().delete()
        Season.objects.all().delete()
        Player.objects.all().delete()

        cls.user = User.objects.create_user(
            username='auth_user', email='auth@example.com', password='password123'
        )

        cls.player1 = Player.objects.create(first_name='Alice', last_name='Smith')
        cls.player2 = Player.objects.create(first_name='Bob', last_name='Jones')
        cls.player3 = Player.objects.create(first_name='Charlie', last_name='Brown')
        cls.player4 = Player.objects.create(first_name='Diana', last_name='Prince')

        today = now().date()
        cls.season_old = Season.objects.create(
            name='2024 Round 1',
            start_date=today - datetime.timedelta(days=200),
            end_date=today - datetime.timedelta(days=140),
            season_round=1,
            is_draft=False,
        )
        cls.season_current = Season.objects.create(
            name='2026 Round 1',
            start_date=today - datetime.timedelta(days=20),
            end_date=today + datetime.timedelta(days=40),
            season_round=1,
            is_draft=False,
        )

        cls.ladder_c1 = Ladder.objects.create(season=cls.season_current, division=1, ladder_type='A')
        cls.ladder_c2 = Ladder.objects.create(season=cls.season_current, division=2, ladder_type='A')
        cls.ladder_old = Ladder.objects.create(season=cls.season_old, division=1, ladder_type='A')

        League.objects.create(ladder=cls.ladder_c1, player=cls.player1, sort_order=1)
        League.objects.create(ladder=cls.ladder_c1, player=cls.player2, sort_order=2)
        League.objects.create(ladder=cls.ladder_c2, player=cls.player3, sort_order=1)
        League.objects.create(ladder=cls.ladder_c2, player=cls.player4, sort_order=2)

        League.objects.create(ladder=cls.ladder_old, player=cls.player1, sort_order=1)
        League.objects.create(ladder=cls.ladder_old, player=cls.player2, sort_order=2)

        # Match 1: Today, Alice beats Bob 9-4 in Div 1
        Result.objects.create(
            ladder=cls.ladder_c1, player=cls.player1, opponent=cls.player2,
            result=9, date_added=today, inaccurate_flag=False,
        )
        Result.objects.create(
            ladder=cls.ladder_c1, player=cls.player2, opponent=cls.player1,
            result=4, date_added=today, inaccurate_flag=False,
        )

        # Match 2: Yesterday, Charlie beats Diana 9-7 in Div 2
        Result.objects.create(
            ladder=cls.ladder_c2, player=cls.player3, opponent=cls.player4,
            result=9, date_added=today - datetime.timedelta(days=1), inaccurate_flag=False,
        )
        Result.objects.create(
            ladder=cls.ladder_c2, player=cls.player4, opponent=cls.player3,
            result=7, date_added=today - datetime.timedelta(days=1), inaccurate_flag=False,
        )

        # Match 3: In OLD season, Bob beats Alice 9-6
        Result.objects.create(
            ladder=cls.ladder_old, player=cls.player2, opponent=cls.player1,
            result=9, date_added=cls.season_old.start_date + datetime.timedelta(days=5), inaccurate_flag=False,
        )
        Result.objects.create(
            ladder=cls.ladder_old, player=cls.player1, opponent=cls.player2,
            result=6, date_added=cls.season_old.start_date + datetime.timedelta(days=5), inaccurate_flag=False,
        )

    def test_season_get_recent_results_normalization_and_relative_dates(self):
        # Anonymous user call (abbreviated last names)
        anon_matches = self.season_current.get_recent_results(user=AnonymousUser(), limit=50)
        self.assertEqual(len(anon_matches), 2)

        # Match 1 should be newest (Today)
        m1 = anon_matches[0]
        self.assertEqual(m1['winner_id'], self.player1.id)
        self.assertEqual(m1['winner_name'], 'Alice S.')
        self.assertEqual(m1['loser_id'], self.player2.id)
        self.assertEqual(m1['loser_name'], 'Bob J.')
        self.assertEqual(m1['winner_score'], 9)
        self.assertEqual(m1['loser_score'], 4)
        self.assertEqual(m1['score_display'], '9 – 4')
        self.assertEqual(m1['division'], 1)
        self.assertEqual(m1['date_display'], 'Today')
        self.assertIn('head_to_head', m1['h2h_url'])

        # Match 2 should be Yesterday
        m2 = anon_matches[1]
        self.assertEqual(m2['winner_id'], self.player3.id)
        self.assertEqual(m2['winner_name'], 'Charlie B.')
        self.assertEqual(m2['loser_name'], 'Diana P.')
        self.assertEqual(m2['winner_score'], 9)
        self.assertEqual(m2['loser_score'], 7)
        self.assertEqual(m2['date_display'], 'Yesterday')
        self.assertEqual(m2['division'], 2)

    def test_season_get_recent_results_authenticated_privacy(self):
        # Authenticated user call (full names)
        auth_matches = self.season_current.get_recent_results(user=self.user, limit=50)
        self.assertEqual(len(auth_matches), 2)
        self.assertEqual(auth_matches[0]['winner_name'], 'Alice Smith')
        self.assertEqual(auth_matches[0]['loser_name'], 'Bob Jones')

    def test_season_get_recent_results_limit(self):
        limited = self.season_current.get_recent_results(user=self.user, limit=1)
        self.assertEqual(len(limited), 1)
        self.assertEqual(limited[0]['winner_id'], self.player1.id)

    def test_homepage_view_renders_recent_results_and_polished_cards(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'ladder/index.html')

        # Check context
        self.assertIn('recent_results', response.context)
        self.assertEqual(len(response.context['recent_results']), 2)

        # Check Recent Results HTML
        self.assertContains(response, 'Recent Results')
        self.assertContains(response, 'Last 2 matches')
        self.assertContains(response, 'Div 1')
        self.assertContains(response, 'Div 2')
        self.assertContains(response, 'Today')
        self.assertContains(response, 'Yesterday')
        self.assertContains(response, '9 – 4')
        self.assertContains(response, '9 – 7')

        # Check H2H modal attributes and lightbox modal inclusion
        self.assertContains(response, 'id="h2hLightboxModal"')
        h2h_url = reverse('head_to_head', kwargs={'player_id': self.player1.id, 'opponent_id': self.player2.id})
        self.assertContains(response, f'data-h2h-url="{h2h_url}"')

        # Check Round Stats link in Progress Graph header
        self.assertContains(response, 'Round Stats &rarr;')
        self.assertContains(response, f"{reverse('stats')}?season={self.season_current.id}")

        # Check Progress Graph hero card and summary badges
        self.assertContains(response, 'Progress')
        self.assertContains(response, 'id="total_divs"')
        self.assertContains(response, 'id="total_players"')
        self.assertContains(response, 'id="total_played"')
        self.assertContains(response, 'id="total_matches"')
        self.assertContains(response, 'id="perc_played"')
        self.assertNotContains(response, 'id="progress_date"')
        self.assertContains(response, 'Matches Played')
        self.assertContains(response, 'Target Pace')
        self.assertContains(response, 'Daily Matches')

        # Check dynamic page size (fallback to 15 since there are 2 divisions)
        self.assertEqual(response.context['results_page_size'], 15)
        self.assertContains(response, 'data-page-size="15"')

        # Check Division Stats progress bars
        self.assertContains(response, 'role="progressbar"')

        # Ensure redundant cards are gone
        self.assertNotContains(response, '<h2>System Stats</h2>')
        self.assertNotContains(response, f'{self.season_current} Stats</h5>')

    def test_homepage_view_empty_state_when_no_matches(self):
        # Remove current season matches
        Result.objects.filter(ladder__season=self.season_current).delete()

        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No matches recorded yet for this round.')
