# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import random
import datetime
import itertools

from django.db import models, migrations


def create_season_data(apps, schema_editor):
    u"""
    Create two seasons
    """
    Season = apps.get_model(u"ladder", u"Season")

    Season(
        season_round=1,
        start_date=u"2014-01-05",
        end_date=u"2014-04-30",
        name=u"Round 1 2014"
    ).save()

    Season(
        season_round=2,
        start_date=u"2014-05-01",
        end_date=u"2014-08-31",
        name=u"Round 2 2014"
    ).save()


def create_player_data(apps, schema_editor):
    u"""
    Create 20 players in a loop
    """
    Player = apps.get_model(u"ladder", u"Player")

    for n in xrange(1, 20):
        Player(
            first_name=u"Player",
            last_name=u"no " + n.__str__(),
            junior=False,
        ).save()


def create_ladder_data(apps, schema_editor):
    u"""
    Create two ladders for each season
    """
    Season = apps.get_model(u"ladder", u"Season")
    Ladder = apps.get_model(u"ladder", u"Ladder")

    for season in Season.objects.all():
        for n in xrange(1, 3):
            Ladder(
                ladder_type=u"First To 9",
                division=n.__str__(),
                season=season
            ).save()


def create_league_data(apps, schema_editor):
    u"""
    Create leagues, add half the players into each.
    """
    Ladder = apps.get_model(u"ladder", u"Ladder")
    Player = apps.get_model(u"ladder", u"Player")
    League = apps.get_model(u"ladder", u"League")

    for ladder in Ladder.objects.all():
        sort_order = 0
        for player in Player.objects.all():
            if (player.id + ladder.id) % 2:
                League(
                    ladder=ladder,
                    sort_order=sort_order,
                    player=player
                ).save()

            sort_order += 10


def create_result_data(apps, schema_editor):
    u"""
    Create results with a 50% play rate
    """
    Ladder = apps.get_model(u"ladder", u"Ladder")
    Result = apps.get_model(u"ladder", u"Result")

    for ladder in Ladder.objects.all():

        # list of all players in a ladder
        players = []
        for league in ladder.league_set.all():
            players.append(league.player.id)

        # loop over unique combinations of players and opponents
        for (idx, (player, opponent)) in enumerate(itertools.combinations(players, 2)):

            if idx % 2 == 0:
                # winner
                Result(
                    ladder=ladder,
                    player_id=player,
                    opponent_id=opponent,
                    result=9,
                    date_added=datetime.datetime.now(),
                    inaccurate_flag=False,
                ).save()

                # loser
                Result(
                    ladder=ladder,
                    player_id=opponent,
                    opponent_id=player,
                    result=random.randrange(0, 8),
                    date_added=datetime.datetime.now(),
                    inaccurate_flag=False,
                ).save()


class Migration(migrations.Migration):
    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name=u'Ladder',
            fields=[
                (u'id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name=u'ID')),
                (u'division', models.CharField(max_length=11)),
                (u'ladder_type', models.CharField(max_length=100)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name=u'League',
            fields=[
                (u'id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name=u'ID')),
                (u'sort_order', models.IntegerField(default=0)),
                (u'ladder', models.ForeignKey(to=u'ladder.Ladder')),
            ],
            options={
                u'ordering': [u'sort_order'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name=u'Player',
            fields=[
                (u'id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name=u'ID')),
                (u'first_name', models.CharField(max_length=100)),
                (u'last_name', models.CharField(max_length=100)),
                (u'home_phone', models.CharField(max_length=100, blank=True)),
                (u'mobile_phone', models.CharField(max_length=100, blank=True)),
                (u'email', models.CharField(max_length=100, blank=True)),
                (u'junior', models.BooleanField(default=None)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name=u'league',
            name=u'player',
            field=models.ForeignKey(to=u'ladder.Player'),
            preserve_default=True,
        ),
        migrations.CreateModel(
            name=u'Result',
            fields=[
                (u'id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name=u'ID')),
                (u'result', models.IntegerField()),
                (u'date_added', models.DateField(verbose_name=u'Date added')),
                (u'inaccurate_flag', models.BooleanField(default=None)),
                (u'ladder', models.ForeignKey(to=u'ladder.Ladder')),
                (u'opponent', models.ForeignKey(to=u'ladder.Player')),
                (u'player', models.ForeignKey(to=u'ladder.Player')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name=u'Season',
            fields=[
                (u'id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name=u'ID')),
                (u'name', models.CharField(max_length=150)),
                (u'start_date', models.DateField(verbose_name=u'Start date')),
                (u'end_date', models.DateField(verbose_name=u'End date')),
                (u'season_round', models.IntegerField(max_length=1)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name=u'ladder',
            name=u'season',
            field=models.ForeignKey(to=u'ladder.Season'),
            preserve_default=True,
        ),
        migrations.RunPython(create_season_data),
        migrations.RunPython(create_player_data),
        migrations.RunPython(create_ladder_data),
        migrations.RunPython(create_league_data),
        migrations.RunPython(create_result_data)
    ]
