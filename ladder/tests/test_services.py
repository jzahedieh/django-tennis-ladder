from django.test import TestCase
from ladder.models import Player, League, Result
from ladder.services.centile import CentileService


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
            expected_centile = round(((total - rank) / total) * 100)
            if expected_best is None or expected_centile > expected_best:
                expected_best = expected_centile

            info = centile_history['by_league_id'][lg.id]
            self.assertEqual(info['rank'], rank)
            self.assertEqual(info['total_players'], total)
            self.assertEqual(info['centile'], expected_centile)

        self.assertEqual(centile_history['best_centile'], f"{expected_best}%")
