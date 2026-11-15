import datetime

from django.contrib.auth.models import AnonymousUser, User
from django.test import TestCase
from django.urls import reverse

from ladder.models import Ladder, League, Player, Result, Season
from ladder.services.centile import CentileService
from ladder.services.grid import LadderGridService


class CentileServiceTest(TestCase):
    def test_fresh_player_empty_history(self):
        fresh = Player.objects.create(first_name='Fresh', last_name='Player')
        data = CentileService.get_player_centile_history(fresh)
        self.assertEqual(data, {
            'by_league_id': {},
            'best_centile': "- %",
            'chart_data': [],
        })

    def test_centile_history_calculation(self):
        player = Player.objects.first()
        centile_history = CentileService.get_player_centile_history(player)

        player_leagues = list(
            League.objects
            .filter(player=player, ladder__season__is_draft=False)
            .select_related('ladder__season')
            .order_by('ladder__season__start_date', 'ladder__season__season_round', 'ladder__division')
        )
        self.assertEqual(len(centile_history['chart_data']), len(player_leagues))

        expected_best = None
        for lg in player_leagues:
            season = lg.ladder.season
            all_lgs = list(
                League.objects
                .filter(ladder__season=season, ladder__season__is_draft=False)
                .select_related('player', 'ladder')
            )

            def get_pts(l):
                res = Result.objects.filter(ladder=l.ladder, player=l.player)
                pts = 0
                for r in res:
                    pts += 12 if r.result == 9 else (r.result + 1)
                return pts

            all_lgs.sort(key=lambda x: (x.ladder.division, -get_pts(x), x.sort_order, x.id))
            rank = [x.id for x in all_lgs].index(lg.id) + 1
            total = len(all_lgs)
            expected_centile = CentileService.calculate_centile(rank, total)
            if expected_best is None or expected_centile > expected_best:
                expected_best = expected_centile

            info = centile_history['by_league_id'][lg.id]
            self.assertEqual(info['rank'], rank)
            self.assertEqual(info['total_players'], total)
            self.assertEqual(info['centile'], expected_centile)

        self.assertEqual(centile_history['best_centile'], f"{expected_best}%")

    def test_calculate_centile_edge_cases(self):
        # Rank 1 is always 100% regardless of ladder size
        self.assertEqual(CentileService.calculate_centile(1, 1), 100)
        self.assertEqual(CentileService.calculate_centile(1, 10), 100)
        self.assertEqual(CentileService.calculate_centile(1, 119), 100)
        self.assertEqual(CentileService.calculate_centile(1, 227), 100)

        # Last rank is always 0%
        self.assertEqual(CentileService.calculate_centile(10, 10), 0)
        self.assertEqual(CentileService.calculate_centile(119, 119), 0)
        self.assertEqual(CentileService.calculate_centile(227, 227), 0)

        # Middle rank
        self.assertEqual(CentileService.calculate_centile(50, 99), 50)

        # Invalid cases
        self.assertIsNone(CentileService.calculate_centile(0, 10))
        self.assertIsNone(CentileService.calculate_centile(1, 0))
        self.assertIsNone(CentileService.calculate_centile(-1, 10))


class LadderGridServiceTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='grid_p1', email='grid_p1@example.com', password='password123'
        )
        cls.p1 = Player.objects.create(first_name='Alice', last_name='Smith', user=cls.user)
        cls.p2 = Player.objects.create(first_name='Bob', last_name='Jones')
        cls.p3 = Player.objects.create(first_name='Charlie', last_name='Brown')
        cls.p4 = Player.objects.create(first_name='Diana', last_name='Prince')

        cls.season = Season.objects.create(
            name='2027 Round 1',
            start_date=datetime.date(2027, 1, 10),
            end_date=datetime.date(2027, 3, 20),
            season_round=1,
            is_draft=False,
        )
        cls.empty_season = Season.objects.create(
            name='2027 Round 2',
            start_date=datetime.date(2027, 4, 1),
            end_date=datetime.date(2027, 6, 1),
            season_round=2,
            is_draft=False,
        )
        cls.div1 = Ladder.objects.create(season=cls.season, division=1, ladder_type='A')
        cls.div2 = Ladder.objects.create(season=cls.season, division=2, ladder_type='A')

        League.objects.create(ladder=cls.div1, player=cls.p1, sort_order=1)
        League.objects.create(ladder=cls.div1, player=cls.p2, sort_order=2)
        League.objects.create(ladder=cls.div1, player=cls.p3, sort_order=3)
        League.objects.create(ladder=cls.div1, player=cls.p4, sort_order=4)

        League.objects.create(ladder=cls.div2, player=cls.p2, sort_order=1)
        League.objects.create(ladder=cls.div2, player=cls.p3, sort_order=2)

        match_date = datetime.date(2027, 2, 1)
        # Div 1: Alice beats Bob 9-0 (verifies 0 score handling) and beats Charlie 9-5
        Result.objects.create(ladder=cls.div1, player=cls.p1, opponent=cls.p2, result=9, date_added=match_date)
        Result.objects.create(ladder=cls.div1, player=cls.p2, opponent=cls.p1, result=0, date_added=match_date)
        Result.objects.create(ladder=cls.div1, player=cls.p1, opponent=cls.p3, result=9, date_added=match_date)
        Result.objects.create(ladder=cls.div1, player=cls.p3, opponent=cls.p1, result=5, date_added=match_date)

        # Div 2: Bob beats Charlie 9-4 (same players, distinct division)
        Result.objects.create(ladder=cls.div2, player=cls.p2, opponent=cls.p3, result=9, date_added=match_date)
        Result.objects.create(ladder=cls.div2, player=cls.p3, opponent=cls.p2, result=4, date_added=match_date)

    def test_calculate_points(self):
        self.assertEqual(LadderGridService.calculate_points(9), 12)
        self.assertEqual(LadderGridService.calculate_points(8), 9)
        self.assertEqual(LadderGridService.calculate_points(7), 8)
        self.assertEqual(LadderGridService.calculate_points(5), 6)
        self.assertEqual(LadderGridService.calculate_points(0), 1)

    def test_calculate_totals_and_average(self):
        self.assertEqual(LadderGridService.calculate_totals_and_average([]), (0, 0))
        self.assertEqual(
            LadderGridService.calculate_totals_and_average([Result(result=9)]),
            (12, '12.00'),
        )
        self.assertEqual(
            LadderGridService.calculate_totals_and_average([Result(result=9), Result(result=5)]),
            (18, '9.00'),
        )
        self.assertEqual(
            LadderGridService.calculate_totals_and_average([0, 8]),
            (10, '5.00'),
        )

    def test_build_ladder_grid_anonymous_and_zero_score(self):
        grid = LadderGridService.build_ladder_grid(self.div1, user=AnonymousUser())
        self.assertEqual(self.div1.grid, grid)
        self.assertEqual(len(grid['rows']), 4)

        row_alice, row_bob, row_charlie, row_diana = grid['rows']

        self.assertEqual(row_alice['position'], 1)
        self.assertEqual(row_alice['player_name'], 'Alice S.')
        self.assertFalse(row_alice['is_current_user'])
        self.assertEqual(row_alice['total'], 24)
        self.assertEqual(row_alice['average'], '12.00')
        self.assertEqual(row_alice['matches_played'], 2)
        self.assertTrue(row_alice['cells'][0]['is_self'])
        self.assertIsNone(row_alice['cells'][0]['result'])
        self.assertEqual(row_alice['cells'][1]['result'], 9)
        self.assertEqual(
            row_alice['cells'][1]['h2h_url'],
            reverse('head_to_head', args=(self.p1.id, self.p2.id)),
        )
        self.assertEqual(row_alice['cells'][1]['h2h_title'], 'Alice S. vs Bob J.')
        self.assertEqual(row_alice['cells'][2]['result'], 9)
        self.assertIsNone(row_alice['cells'][3]['result'])

        # Bob lost 0-9 to Alice -> result is integer 0, total = 1, avg = '1.00'
        self.assertEqual(row_bob['position'], 2)
        self.assertEqual(row_bob['total'], 1)
        self.assertEqual(row_bob['average'], '1.00')
        self.assertEqual(row_bob['matches_played'], 1)
        self.assertIs(row_bob['cells'][0]['result'], 0)
        self.assertTrue(row_bob['cells'][1]['is_self'])
        self.assertIsNone(row_bob['cells'][2]['result'])

        # Charlie lost 5-9 to Alice -> total = 6, avg = '6.00'
        self.assertEqual(row_charlie['total'], 6)
        self.assertEqual(row_charlie['average'], '6.00')
        self.assertEqual(row_charlie['cells'][0]['result'], 5)

        # Diana has no matches -> total = 0, avg = 0
        self.assertEqual(row_diana['total'], 0)
        self.assertEqual(row_diana['average'], 0)
        self.assertEqual(row_diana['matches_played'], 0)

    def test_build_ladder_grid_authenticated_and_prefetched_queries(self):
        prefetched_ladder = (
            Ladder.objects.filter(pk=self.div1.pk)
            .prefetch_related('league_set__player__user')
            .get()
        )
        prefetched_results = list(Result.objects.filter(ladder=prefetched_ladder))

        with self.assertNumQueries(0):
            grid = LadderGridService.build_ladder_grid(
                prefetched_ladder,
                user=self.user,
                results=prefetched_results,
            )

        row_alice, row_bob, _, _ = grid['rows']
        self.assertEqual(row_alice['player_name'], 'Alice Smith')
        self.assertTrue(row_alice['is_current_user'])
        self.assertEqual(row_alice['cells'][1]['h2h_title'], 'Alice Smith vs Bob Jones')
        self.assertEqual(row_bob['player_name'], 'Bob Jones')
        self.assertFalse(row_bob['is_current_user'])

    def test_build_season_grids_scopes_results_per_division(self):
        ladders = LadderGridService.build_season_grids(self.season, user=self.user)
        self.assertEqual(len(ladders), 2)

        by_div = {ldr.division: ldr.grid for ldr in ladders}
        div1_bob = next(r for r in by_div[1]['rows'] if r['player_id'] == self.p2.id)
        div2_bob = next(r for r in by_div[2]['rows'] if r['player_id'] == self.p2.id)

        self.assertEqual(div1_bob['total'], 1)
        self.assertEqual(div1_bob['average'], '1.00')
        self.assertEqual(div2_bob['total'], 12)
        self.assertEqual(div2_bob['average'], '12.00')

        self.assertEqual(LadderGridService.build_season_grids(self.empty_season), [])

