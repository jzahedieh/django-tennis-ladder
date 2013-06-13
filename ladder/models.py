from django.db import models
from django import forms
import operator


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

        return {'player':player,  'total':totals[player]}


class Result(models.Model):
    ladder = models.ForeignKey(Ladder)
    player = models.ForeignKey(Player, related_name='result_player')
    opponent = models.ForeignKey(Player, related_name='result_opponent')
    result = models.IntegerField()
    date_added = models.DateField('Date added')

    def __unicode__(self):
        return self.player.first_name + ' ' + self.player.last_name + ' vs ' + self.opponent.first_name + ' ' + self.opponent.last_name
