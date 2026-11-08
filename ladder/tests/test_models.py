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

    def test_get_centile_history_delegates(self):
        """
        Verifies Player.get_centile_history delegates to CentileService.
        """
        player = Player.objects.first()
        history = player.get_centile_history()
        self.assertIn('by_league_id', history)
        self.assertIn('best_centile', history)
        self.assertIn('chart_data', history)



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


class LadderModelTest(TestCase):
    def test_get_email_latest_and_template_rendering(self):
        from django.contrib.auth.models import User
        from django.template.loader import get_template
        from django.utils.timezone import now
        from ladder.models import Ladder

        today = now().date()
        season = Season.objects.create(name='Test 2026', start_date=today, end_date=today, season_round=1, is_draft=False)
        ladder = Ladder.objects.create(season=season, division=1)
        user = User.objects.create_user(username='sub_user', email='sub@example.com')
        p1 = Player.objects.create(first_name='Alpha', last_name='One', user=user)
        p2 = Player.objects.create(first_name='Beta', last_name='Two')
        p3 = Player.objects.create(first_name='Gamma', last_name='Three')

        # 1. Incomplete (Time) match: Alpha 5 - 5 Beta
        t_now = now()
        Result.objects.create(ladder=ladder, player=p1, opponent=p2, result=5, incomplete_reason=Result.IncompleteReason.TIME, date_added=t_now)
        Result.objects.create(ladder=ladder, player=p2, opponent=p1, result=5, incomplete_reason=Result.IncompleteReason.TIME, date_added=t_now)

        # 2. Injury retirement match: Alpha 9 - 4 Gamma (Gamma retired)
        Result.objects.create(ladder=ladder, player=p1, opponent=p3, result=9, incomplete_reason=Result.IncompleteReason.INJURY, date_added=t_now)
        Result.objects.create(ladder=ladder, player=p3, opponent=p1, result=4, incomplete_reason=Result.IncompleteReason.INJURY, date_added=t_now)

        buckets = ladder.get_email_latest(days=1, limit=5)
        new_items = buckets['new']
        self.assertEqual(len(new_items), 2)

        # Check incomplete time match metadata
        time_item = next(item for item in new_items if item['opponent'] == p2 or item['player'] == p2)
        self.assertTrue(time_item['is_incomplete'])
        self.assertFalse(time_item['is_injury'])
        self.assertEqual(time_item['status_label'], '(Inc.)')

        # Check injury retirement match metadata
        injury_item = next(item for item in new_items if item['opponent'] == p3 or item['player'] == p3)
        self.assertTrue(injury_item['is_injury'])
        self.assertFalse(injury_item['is_incomplete'])
        self.assertEqual(injury_item['status_label'], '(Ret.)')
        self.assertEqual(injury_item['player_result'], 9)  # Winner ordered first

        # Check template rendering
        rendered = get_template("ladder/ladder/subscription/email.html").render({
            'ladder': ladder,
            'user': user,
            'unsubscribe_url': 'https://highgate-ladder.co.uk/unsubscribe/token123/',
            'protocol': 'https',
            'domain': 'highgate-ladder.co.uk'
        })
        self.assertIn('(Inc.)', rendered)
        self.assertIn('(Ret.)', rendered)
