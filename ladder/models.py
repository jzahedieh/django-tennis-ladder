import operator

from django.db import models


class Season(models.Model):
    name = models.CharField(max_length=150)
    start_date = models.DateField('Start date')
    end_date = models.DateField('End date')

    def __unicode__(self):
        return self.name


class Player(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    home_phone = models.CharField(max_length=100)
    mobile_phone = models.CharField(max_length=100)
    email = models.CharField(max_length=100)
    junior = models.BooleanField(default=False)

    def __unicode__(self):
        return self.first_name + ' ' + self.last_name


class Ladder(models.Model):
    season = models.ForeignKey(Season)
    division = models.IntegerField(default=0)
    ladder_type = models.CharField(max_length=100)
    players = models.ManyToManyField(Player)

    def __unicode__(self):
        return self.season.name + ' division: ' + str(self.division)

    def get_leader(self):
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

        player = max(totals.iteritems(), key=operator.itemgetter(1))[0]

        return {'player': player,  'total': totals[player]}

    def get_latest_results(self):
        results = {}
        for result in self.result_set.filter(ladder=self).order_by('-date_added')[:10]:  # [:10] to limit to 5

            opponent = self.result_set.filter(ladder=self, player=result.opponent, opponent=result.player)[0]
            player_opponent_index = ''.join(str(e) for e in sorted([result.player.id, opponent.player.id]))
            try:
                if results[player_opponent_index]:
                    continue
            except KeyError:
                results[player_opponent_index] = {'player': result.player, 'player_result': result.result,
                                                  'opponent_result': opponent.result, 'opponent': opponent.player,
                                                  'date_added': result.date_added}

        ordered_results = {}
        i = 0
        for key in sorted(results, key=lambda x: (results[x]['date_added']), reverse=True):
            ordered_results[i] = results[key]
            i += 1

        return ordered_results.items()

    def get_stats(self):
        total_matches_played = 0.00
        total_matches = self.players.count() * (self.players.count() - 1) / 2
        total_matches_played += self.result_set.count() / 2
        perc_matches_played = (total_matches_played / total_matches) * 100

        return {
            'total_matches_played': total_matches_played,
            'total_matches': total_matches,
            'perc_matches_played': perc_matches_played
            }


class Result(models.Model):
    ladder = models.ForeignKey(Ladder)
    player = models.ForeignKey(Player, related_name='result_player')
    opponent = models.ForeignKey(Player, related_name='result_opponent')
    result = models.IntegerField()
    date_added = models.DateField('Date added')

    def __unicode__(self):
        return self.player.first_name + ' ' + self.player.last_name + ' vs ' + self.opponent.first_name + ' ' + self.opponent.last_name
