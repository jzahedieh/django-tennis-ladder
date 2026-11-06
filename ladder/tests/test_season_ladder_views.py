import datetime
from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from ladder.models import Ladder, LadderSubscription, League, Player, Result, Season


class SeasonAndLadderViewsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        Result.objects.all().delete()
        League.objects.all().delete()
        Ladder.objects.all().delete()
        Season.objects.all().delete()
        Player.objects.all().delete()

        cls.user = User.objects.create_user(
            username='player1_user', email='p1@example.com', password='password123'
        )
        cls.superuser = User.objects.create_superuser(
            username='admin_user', email='admin@example.com', password='password123'
        )

        cls.player1 = Player.objects.create(first_name='Alice', last_name='Smith', user=cls.user)
        cls.player2 = Player.objects.create(first_name='Bob', last_name='Jones')
        cls.player3 = Player.objects.create(first_name='Charlie', last_name='Brown')

        today = datetime.date.today()
        cls.season_old = Season.objects.create(
            name='2024 Round 1',
            start_date=datetime.date(2024, 1, 10),
            end_date=datetime.date(2024, 3, 20),
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
        cls.season_draft = Season.objects.create(
            name='2026 Round 2 Draft',
            start_date=today + datetime.timedelta(days=50),
            end_date=today + datetime.timedelta(days=100),
            season_round=2,
            is_draft=True,
        )

        # Current season: Div 1 (3 players -> 3 matches), Div 2 (2 players -> 1 match)
        cls.ladder_c_div1 = Ladder.objects.create(season=cls.season_current, division=1, ladder_type='A')
        cls.ladder_c_div2 = Ladder.objects.create(season=cls.season_current, division=2, ladder_type='A')

        League.objects.create(ladder=cls.ladder_c_div1, player=cls.player1, sort_order=1)
        League.objects.create(ladder=cls.ladder_c_div1, player=cls.player2, sort_order=2)
        League.objects.create(ladder=cls.ladder_c_div1, player=cls.player3, sort_order=3)

        League.objects.create(ladder=cls.ladder_c_div2, player=cls.player2, sort_order=1)
        League.objects.create(ladder=cls.ladder_c_div2, player=cls.player3, sort_order=2)

        # Old season: Div 1 (2 players -> 1 match)
        cls.ladder_o_div1 = Ladder.objects.create(season=cls.season_old, division=1, ladder_type='A')
        League.objects.create(ladder=cls.ladder_o_div1, player=cls.player1, sort_order=1)
        League.objects.create(ladder=cls.ladder_o_div1, player=cls.player2, sort_order=2)

        # Play 1 match in current season Div 1 (Alice 9 - 5 Bob)
        Result.objects.create(
            ladder=cls.ladder_c_div1,
            player=cls.player1,
            opponent=cls.player2,
            result=9,
            date_added=today - datetime.timedelta(days=5),
            inaccurate_flag=False,
        )
        Result.objects.create(
            ladder=cls.ladder_c_div1,
            player=cls.player2,
            opponent=cls.player1,
            result=5,
            date_added=today - datetime.timedelta(days=5),
            inaccurate_flag=False,
        )

        # Play 1 match in old season Div 1 (Bob 9 - 7 Alice)
        Result.objects.create(
            ladder=cls.ladder_o_div1,
            player=cls.player2,
            opponent=cls.player1,
            result=9,
            date_added=datetime.date(2024, 2, 1),
            inaccurate_flag=False,
        )
        Result.objects.create(
            ladder=cls.ladder_o_div1,
            player=cls.player1,
            opponent=cls.player2,
            result=7,
            date_added=datetime.date(2024, 2, 1),
            inaccurate_flag=False,
        )

    def test_list_rounds_bulk_stats_and_template(self):
        response = self.client.get(reverse('list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'ladder/season/list.html')

        seasons = response.context['seasons']
        summary = response.context['summary']

        # Draft season excluded; ordered newest first
        self.assertEqual(len(seasons), 2)
        self.assertEqual(seasons[0].id, self.season_current.id)
        self.assertEqual(seasons[1].id, self.season_old.id)

        # Current season stats: 2 divisions, 5 players, 4 total matches (3 + 1), 1 match played (25.00%)
        s_curr = seasons[0]
        self.assertEqual(s_curr.divisions_count, 2)
        self.assertEqual(s_curr.player_count, 5)
        self.assertEqual(s_curr.total_matches, 4)
        self.assertEqual(s_curr.matches_played, 1)
        self.assertEqual(s_curr.percentage_played, '25.00')
        self.assertTrue(s_curr.is_latest)

        # Old season stats: 1 division, 2 players, 1 total match, 1 match played (100.00%)
        s_old = seasons[1]
        self.assertEqual(s_old.divisions_count, 1)
        self.assertEqual(s_old.player_count, 2)
        self.assertEqual(s_old.total_matches, 1)
        self.assertEqual(s_old.matches_played, 1)
        self.assertEqual(s_old.percentage_played, '100.00')
        self.assertFalse(s_old.is_latest)

        # Summary KPIs
        self.assertEqual(summary['total_seasons'], 2)
        self.assertEqual(summary['total_divisions'], 3)
        self.assertEqual(summary['total_matches_played'], 2)
        self.assertEqual(summary['total_matches_scheduled'], 5)
        self.assertEqual(summary['overall_completion'], '40.0%')

        # Ensure per-row AJAX loop is removed and stats are rendered in HTML
        self.assertNotContains(response, '/season/ajax/stats/')
        self.assertContains(response, '25.00%')
        self.assertContains(response, '100.00%')

    def test_season_view_links_avg_h2h_modal_and_user_highlight(self):
        url = reverse('season', args=(self.season_current.start_date.year, self.season_current.season_round))

        # Anonymous request
        anon_resp = self.client.get(url)
        self.assertEqual(anon_resp.status_code, 200)
        self.assertContains(anon_resp, reverse('player_history', args=(self.player1.id,)))
        self.assertContains(anon_resp, 'Avg')
        self.assertContains(anon_resp, 'id="h2hLightboxModal"')
        self.assertContains(
            anon_resp,
            f'data-h2h-url="{reverse("head_to_head", args=(self.player1.id, self.player2.id))}"',
        )
        self.assertNotContains(anon_resp, 'current-user-row')

        # Authenticated request as player1
        self.client.login(username='player1_user', password='password123')
        auth_resp = self.client.get(url)
        self.assertEqual(auth_resp.status_code, 200)
        self.assertContains(auth_resp, 'current-user-row')

    def test_ladder_view_subscription_button_h2h_modal_and_user_highlight(self):
        url = reverse(
            'ladder',
            args=(self.season_current.start_date.year, self.season_current.season_round, 1),
        )
        sub_url = reverse(
            'ladder_subscription',
            args=(self.season_current.start_date.year, self.season_current.season_round, 1),
        )

        # 1. Anonymous user: no subscription button, no current-user-row, H2H modal present
        anon_resp = self.client.get(url)
        self.assertEqual(anon_resp.status_code, 200)
        self.assertNotContains(anon_resp, sub_url)
        self.assertNotContains(anon_resp, 'current-user-row')
        self.assertContains(anon_resp, 'id="h2hLightboxModal"')
        self.assertContains(
            anon_resp,
            f'data-h2h-url="{reverse("head_to_head", args=(self.player1.id, self.player2.id))}"',
        )

        # 2. Authenticated player1 (auto-subscribed on League creation): shows Unsubscribe button and row highlight
        self.client.login(username='player1_user', password='password123')
        auth_resp = self.client.get(url)
        self.assertEqual(auth_resp.status_code, 200)
        self.assertContains(auth_resp, sub_url)
        self.assertContains(auth_resp, 'Unsubscribe')
        self.assertContains(auth_resp, 'current-user-row')

        # Remove subscription -> shows Subscribe button
        LadderSubscription.objects.filter(user=self.user, ladder=self.ladder_c_div1).delete()
        unsub_resp = self.client.get(url)
        self.assertContains(unsub_resp, 'Subscribe')
        self.assertNotContains(unsub_resp, 'Unsubscribe')

        # 3. Superuser: subscription button is visible and subscription can be toggled
        self.client.login(username='admin_user', password='password123')
        admin_resp = self.client.get(url)
        self.assertEqual(admin_resp.status_code, 200)
        self.assertContains(admin_resp, sub_url)
        self.assertContains(admin_resp, 'Subscribe')

        # Superuser can subscribe successfully
        post_sub_resp = self.client.get(sub_url, follow=True)
        self.assertEqual(post_sub_resp.status_code, 200)
        self.assertContains(post_sub_resp, 'Unsubscribe')

    def test_index_view_server_side_stats_and_no_ajax(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'ladder/index.html')

        # Check context has server-side stats, leaders, and chart data
        self.assertIn('season_stats', response.context)
        self.assertIn('current_leaders', response.context)
        self.assertIn('progress_json', response.context)
        self.assertIn('progress_data', response.context)

        # Ensure no AJAX calls to old endpoints are in the rendered HTML
        self.assertNotContains(response, '/season/ajax/stats/')
        self.assertNotContains(response, '/season/ajax/progress/')

        # Ensure server-side rendered division names and stats are present in the HTML
        self.assertContains(response, 'Division 1')
        self.assertContains(response, 'Division 2')

        # Verify old AJAX endpoints no longer exist
        ajax_stats_resp = self.client.get('/season/ajax/stats/?id=1')
        self.assertEqual(ajax_stats_resp.status_code, 404)
        ajax_progress_resp = self.client.get('/season/ajax/progress/?id=1')
        self.assertEqual(ajax_progress_resp.status_code, 404)

    def test_ladder_view_revamped_stats_and_latest_results_cards(self):
        # Add a second match in Div 1: Charlie beats Bob 9-8 today
        today = datetime.date.today()
        Result.objects.create(
            ladder=self.ladder_c_div1,
            player=self.player3,
            opponent=self.player2,
            result=9,
            date_added=today,
            inaccurate_flag=False,
        )
        Result.objects.create(
            ladder=self.ladder_c_div1,
            player=self.player2,
            opponent=self.player3,
            result=8,
            date_added=today,
            inaccurate_flag=False,
        )

        url = reverse(
            'ladder',
            args=(self.season_current.start_date.year, self.season_current.season_round, 1),
        )

        # 1. Anonymous user request (abbreviated surnames)
        anon_resp = self.client.get(url)
        self.assertEqual(anon_resp.status_code, 200)
        self.assertIn('division_stats', anon_resp.context)
        self.assertIn('recent_results', anon_resp.context)

        stats = anon_resp.context['division_stats']
        self.assertEqual(stats['players_count'], 3)
        self.assertEqual(stats['total_matches'], 3)
        self.assertEqual(stats['total_matches_played'], 2)
        self.assertEqual(stats['matches_remaining'], 1)
        self.assertAlmostEqual(stats['perc_matches_played'], 66.6666, places=2)

        # Bob has 2 matches (5+1=6 and 8+1=9 -> 15 pts), Alice has 12 pts, Charlie has 12 pts
        self.assertEqual(stats['leader']['player_id'], self.player2.id)
        self.assertEqual(stats['leader']['player_name'], 'Bob J.')
        self.assertEqual(stats['leader']['total'], 15)
        self.assertEqual(stats['avg_match_score'], '9 – 6.5')
        self.assertEqual(stats['avg_games_per_match'], '15.5')
        self.assertEqual(stats['total_games_played'], 31)
        self.assertEqual(stats['close_matches_count'], 1)
        self.assertAlmostEqual(stats['close_matches_pct'], 50.0)

        # Check rendered HTML cards, profile links, H2H links, and progress bar
        self.assertContains(anon_resp, 'Division 1 Stats')
        self.assertContains(anon_resp, '3 Players')
        self.assertContains(anon_resp, 'Round Stats &rarr;')
        self.assertContains(anon_resp, '2 of 3 scheduled matches (1 remaining)')
        self.assertContains(anon_resp, '66.67%')
        self.assertContains(anon_resp, 'role="progressbar"')
        self.assertContains(anon_resp, 'Current Leader')
        self.assertContains(anon_resp, 'Average Match Score')
        self.assertContains(anon_resp, '9 – 6.5')
        self.assertContains(anon_resp, '15.5 games per match (31 total games)')
        self.assertContains(anon_resp, 'Close Matches (9&ndash;7 / 9&ndash;8)')
        self.assertContains(anon_resp, '1 of 2 matches decided by 1&ndash;2 games')
        self.assertContains(anon_resp, '1 (50%)')
        self.assertNotContains(anon_resp, 'Highest Average')
        self.assertNotContains(anon_resp, 'Most Matches Played')
        self.assertNotContains(anon_resp, 'Closest Match')
        self.assertNotContains(anon_resp, 'Biggest Win')
        self.assertContains(anon_resp, 'Latest Results')
        self.assertContains(anon_resp, '2 matches')
        self.assertContains(anon_resp, '9 – 8')
        self.assertContains(anon_resp, '9 – 5')
        self.assertContains(anon_resp, 'Today')
        self.assertContains(anon_resp, reverse('player_history', args=(self.player1.id,)))
        self.assertContains(anon_resp, reverse('player_history', args=(self.player2.id,)))
        self.assertContains(anon_resp, reverse('player_history', args=(self.player3.id,)))
        self.assertContains(
            anon_resp,
            f'data-h2h-url="{reverse("head_to_head", args=(self.player3.id, self.player2.id))}"',
        )

        # 2. Authenticated user sees full names in stats and latest results
        self.client.login(username='player1_user', password='password123')
        auth_resp = self.client.get(url)
        self.assertEqual(auth_resp.status_code, 200)
        self.assertContains(auth_resp, 'Bob Jones')
        self.assertContains(auth_resp, 'Charlie Brown')
        self.assertContains(auth_resp, 'Alice Smith')

        # 3. Division with no matches shows empty states cleanly
        div2_url = reverse(
            'ladder',
            args=(self.season_current.start_date.year, self.season_current.season_round, 2),
        )
        div2_resp = self.client.get(div2_url)
        self.assertEqual(div2_resp.status_code, 200)
        self.assertContains(div2_resp, 'Division 2 Stats')
        self.assertContains(div2_resp, 'No matches played yet')
        self.assertContains(div2_resp, 'No matches recorded yet for this division.')

    def test_admin_url_configurable_and_in_navbar(self):
        admin_url = reverse('admin:index')
        self.assertEqual(admin_url, f'/{settings.ADMIN_URL}/')

        # When logged in as superuser, the navbar dropdown links to admin_url
        self.client.login(username='admin_user', password='password123')
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'href="{admin_url}"')

