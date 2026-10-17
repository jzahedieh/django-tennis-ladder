from django.test import TestCase
from ladder.models import Player, Result, League, Season
from django.db.models import Avg


class PlayerModelTest(TestCase):
    def test_player_stats(self):
        """
        Tests a player stats is calculated correctly.
        """
        # fresh player test
        player = Player(first_name='New', last_name='Player')
        player.save()
        self.assertEqual(player.player_stats(), {
            'played': "-",
            'win_rate': "- %",
            'average': "-"
        })

        # player with matches test
        player = Player.objects.first()
        stats = player.player_stats()
        results = Result.objects.filter(player=player)

        # assert games played is correct
        games_played = results.count()
        self.assertEqual(stats['played'], games_played)

        # assert completion rate is correct
        match_count = 0
        for league in League.objects.filter(player=player):
            match_count += league.ladder.league_set.count() - 1

        self.assertEqual(stats['completion_rate'], "{0:.2f} %".format(games_played / match_count * 100.00))

        # assert win rate is correct
        won = player.result_player.filter(result=9).count()
        self.assertEqual(stats['win_rate'], "{0:.2f} %".format(won / games_played * 100.00))

        # assert average is correct
        # two points for winning + 1 point for playing
        additional_points = ((won * 2) + games_played) / games_played
        average = list(player.result_player.aggregate(Avg('result')).values())[0]
        average_with_additional = average + additional_points
        self.assertEqual(stats['average'], "{0:.2f}".format(average_with_additional))

    def test_get_centile_history(self):
        """
        Tests player centile history calculation across seasons and divisions.
        """
        # Fresh player with no leagues
        fresh = Player.objects.create(first_name='Fresh', last_name='Player')
        self.assertEqual(fresh.get_centile_history(), {
            'by_league_id': {},
            'best_centile': "- %",
            'chart_data': [],
        })

        # Existing player with leagues across seasons
        player = Player.objects.first()
        centile_history = player.get_centile_history()
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
            # Build expected ranking using points
            all_lgs = list(
                League.objects
                .filter(ladder__season=season, ladder__season__is_draft=False)
                .select_related('player', 'ladder')
            )
            # Calculate points for each league
            def get_pts(l):
                res = Result.objects.filter(ladder=l.ladder, player=l.player)
                pts = 0
                for r in res:
                    pts += 12 if r.result == 9 else (r.result + 1)
                return pts

            all_lgs.sort(key=lambda x: (x.ladder.division, -get_pts(x), x.sort_order, x.id))
            rank = [x.id for x in all_lgs].index(lg.id) + 1
            total = len(all_lgs)
            expected_centile = round((rank / total) * 100)
            if expected_best is None or expected_centile < expected_best:
                expected_best = expected_centile

            info = centile_history['by_league_id'][lg.id]
            self.assertEqual(info['rank'], rank)
            self.assertEqual(info['total_players'], total)
            self.assertEqual(info['centile'], expected_centile)

        self.assertEqual(centile_history['best_centile'], f"{expected_best}%")


class SeasonModelTest(TestCase):

    def test_season_stats(self):

        season = Season.objects.first()
        stats = season.get_stats()

        player_count = 0
        results_count = 0
        total_games_count = 0.0
        for ladder in season.ladder_set.all():
            player_count += ladder.league_set.count()
            results_count += ladder.result_set.count() / 2
            total_games_count += (ladder.league_set.count() * (ladder.league_set.count() - 1)) / 2

        # division stat assertion
        self.assertEqual(stats['divisions'], season.ladder_set.count())

        # perc played assertion
        percentage_played = (results_count / total_games_count) * 100
        self.assertEqual(stats['percentage_played'], "{0:.2f}".format(percentage_played))

        # total games assertion
        self.assertEqual(stats['total_games_count'], total_games_count)

        # result count assertion
        self.assertEqual(stats['results_count'], results_count)

        # player count assertion
        self.assertEqual(stats['player_count'], player_count)