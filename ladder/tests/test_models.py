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