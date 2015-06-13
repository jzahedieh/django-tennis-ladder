from __future__ import division
import operator
from django.db import models
from django.db.models import Avg


class Season(models.Model):
    name = models.CharField(max_length=150)
    start_date = models.DateField(u'Start date')
    end_date = models.DateField(u'End date')
    season_round = models.IntegerField(max_length=1)

    def __str__(self):
        return unicode(self.start_date.year) + u' Round ' + unicode(self.season_round)

    def get_stats(self):
        u"""
        Generates the season stats
        """
        player_count = 0
        results_count = 0
        total_games_count = 0.0
        for ladder in self.ladder_set.all():
            player_count += ladder.league_set.count()
            results_count += ladder.result_set.count() / 2
            total_games_count += (ladder.league_set.count() * (ladder.league_set.count() - 1)) / 2

        percentage_played = (results_count / total_games_count) * 100

        return {
            u'divisions': self.ladder_set.count(),
            u'percentage_played': u"{0:.2f}".format(percentage_played),
            u'total_games_count': total_games_count,
            u'results_count': results_count,
            u'player_count': player_count
        }

    def get_leader_stats(self):
        u"""
        Generates the list of leaders for current season
        """
        current_leaders = {}

        for ladder in self.ladder_set.all():
            current_leaders[ladder.id] = ladder.get_leader()

        return {
            u'current_leaders': current_leaders,
        }

    def get_progress(self):
        u"""
        Query how many games have been played so far.
        """
        results = Result.objects.raw(u"""
            SELECT ladder_result.id, ladder_id, season_id, date_added, COUNT(*) AS added_count
            FROM ladder_result LEFT JOIN ladder_ladder
            ON ladder_result.ladder_id=ladder_ladder.id
            WHERE season_id = %s GROUP BY DATE(date_added)
            ORDER BY DATE(date_added) ASC;
        """, [self.id])

        leagues = League.objects.raw(u"""
            SELECT ladder_league.id, COUNT(*) AS player_count
            FROM ladder_league LEFT JOIN ladder_ladder
            ON ladder_league.ladder_id=ladder_ladder.id
            WHERE season_id = %s GROUP BY ladder_id;
        """, [self.id])

        played = []
        played_days = []
        played_cumulative = []
        played_cumulative_count = 0
        latest_result = False

        for result in results:
            played.append(result.added_count)
            played_days.append((result.date_added - self.start_date).days)

            played_cumulative_count += result.added_count / 2
            played_cumulative.append(played_cumulative_count)
            latest_result = result.date_added

        total_matches = 0
        for league in leagues:
            total_matches += (league.player_count-1) * league.player_count / 2

        return {
            u"season_days": [0, (self.end_date - self.start_date).days],
            u"season_total_matches": [0, total_matches],
            u"played_days": played_days,
            u"played": played,
            u"played_cumulative": played_cumulative,
            u"latest_result": latest_result.strftime(u"%B %d, %Y") if latest_result else "-"
        }


class Player(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    def __str__(self):
        string = self.first_name
        if self.last_name:
            last_names = self.last_name.split()
            last_names[-1] = last_names[-1][:1].capitalize() + u'.'  # abbreviate last name
            string += u' ' + u' '.join(last_names)

        return string

    def player_stats(self):
        u"""
        Calculates stats about the players historical performance.
        """
        played = self.result_player.count()
        won = float(self.result_player.filter(result=9).count())
        lost = played - won  # more efficient than doing a count on the object

        # safe division (not by 0)
        if played != 0:
            win_rate = won / float(played) * 100.00
            # 2 points for winning, 1 for playing
            additional_points = ((won * 2) + played) / played
        else:
            return {
                u'played': u"-",
                u'win_rate': u"- %",
                u'average': u"-"
            }

        # work out the average with additional points
        average = list(self.result_player.aggregate(Avg(u'result')).values())[0]
        average_with_additional = average + additional_points

        leagues = self.league_set.filter(player=self)

        match_count = 0
        for league in leagues:
            # count other players in ladder minus the player to get games
            match_count += league.ladder.league_set.count() - 1

        completion_rate = float(played) / float(match_count) * 100.00

        return {
            u'played': played,
            u'win_rate': u"{0:.2f} %".format(win_rate),
            u'completion_rate': u"{0:.2f} %".format(completion_rate),
            u'average': u"{0:.2f}".format(average_with_additional)
        }


class Ladder(models.Model):
    season = models.ForeignKey(Season)
    division = models.CharField(max_length=11)
    ladder_type = models.CharField(max_length=100)

    def __str__(self):
        return unicode(self.season.start_date.year) + u' Round ' + unicode(self.season.season_round) + u' - Division: ' + unicode(
            self.division)

    def get_leader(self):
        u"""
        Finds the leader of the ladder
        """
        totals = {}
        for result in self.result_set.filter(ladder=self):
            try:
                if result.result == 9:
                    totals[result.player] += int(result.result) + 3
                else:
                    totals[result.player] += int(result.result) + 1
            except KeyError:
                if result.result == 9:
                    totals[result.player] = int(result.result) + 3
                else:
                    totals[result.player] = int(result.result) + 1

        if totals:
            player = max(iter(totals.items()), key=operator.itemgetter(1))[0]
        else:
            return {u'player': u'No Results', u'player_id': u'../#', u'total': u'-', u'division': self.division}

        return {u'player': player.__str__(), u'player_id': player.id, u'total': totals[player], u'division': self.division}

    def get_latest_results(self):
        u"""
        Gets latest results for the ladder
        """
        results = {}
        for result in self.result_set.filter(ladder=self).order_by(u'-date_added')[:10]:  # [:10] to limit to 5

            try:
                opponent = self.result_set.filter(ladder=self, player=result.opponent, opponent=result.player)[0]
            except IndexError:
                continue  # this exception happens if result does not have opponent
            player_opponent_index = u''.join(unicode(e) for e in sorted([result.player.id, opponent.player.id]))
            try:
                if results[player_opponent_index]:
                    continue
            except KeyError:
                results[player_opponent_index] = {u'player': result.player, u'player_result': result.result,
                                                  u'opponent_result': opponent.result, u'opponent': opponent.player,
                                                  u'date_added': result.date_added}

        ordered_results = {}
        i = 0
        for key in sorted(results, key=lambda x: (results[x][u'date_added']), reverse=True):
            ordered_results[i] = results[key]
            i += 1

        return list(ordered_results.items())

    def get_stats(self):
        u"""
        Generates the stats for current division
        """
        total_matches_played = 0.00
        total_matches = self.league_set.count() * (self.league_set.count() - 1) / 2
        total_matches_played += self.result_set.count() / 2
        perc_matches_played = (total_matches_played / total_matches) * 100

        return {
            u'total_matches_played': int(total_matches_played),
            u'total_matches': int(total_matches),
            u'perc_matches_played': perc_matches_played
        }


class League(models.Model):
    ladder = models.ForeignKey(Ladder)
    player = models.ForeignKey(Player)
    sort_order = models.IntegerField(default=0)

    class Meta(object):
        ordering = [u'sort_order']

    def __str__(self):
        return self.player.first_name + u' ' + self.player.last_name

    def player_stats(self):
        u"""
        Generates the player stats for player listings
        """
        total_points = 0.00
        games = 0.00
        won_count = 0
        for result in self.player.result_player.filter(player=self.player, ladder=self.ladder):

            if result.result == 9:
                total_points += (result.result + 2 + 1)  # two for winning one for playing
                won_count += 1
            else:
                total_points += (result.result + 1)  # one for playing

            games += 1

        # work out points per match
        if games > 0:
            pointsdivgames = total_points / games
            percplayed = games / (self.ladder.league_set.count() - 1) * 100
        else:
            percplayed = pointsdivgames = 0

        return {
            u'total_points': total_points,
            u'games': games,
            u'pointsdivgames': pointsdivgames,
            u'won_count': won_count,
            u'percplayed': percplayed
        }


class Result(models.Model):
    ladder = models.ForeignKey(Ladder)
    player = models.ForeignKey(Player, related_name=u'result_player')
    opponent = models.ForeignKey(Player, related_name=u'result_opponent')
    result = models.IntegerField()
    date_added = models.DateField(u'Date added')
    inaccurate_flag = models.BooleanField(default=None)

    def __str__(self):
        return (self.player.first_name + u' ' + self.player.last_name) + u' vs ' + (
            self.opponent.first_name + u' ' + self.opponent.last_name) + (u' score: ' + unicode(self.result))