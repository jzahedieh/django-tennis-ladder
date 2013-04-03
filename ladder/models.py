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


class Result(models.Model):
    ladder = models.ForeignKey(Ladder)
    player = models.ForeignKey(Player, related_name='result_player')
    opponent = models.ForeignKey(Player, related_name='result_opponent')
    result = models.IntegerField()
    date_added = models.DateField('Date added')

    def __unicode__(self):
        return self.player.first_name + ' ' + self.player.last_name + ' vs ' + self.opponent.first_name + ' ' + self.opponent.last_name
