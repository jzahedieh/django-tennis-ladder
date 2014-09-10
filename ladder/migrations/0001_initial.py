# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import random
import datetime
import itertools

from django.db import models, migrations


def create_season_data(apps, schema_editor):
    """
    Create two seasons
    """
    Season = apps.get_model("ladder", "Season")

    Season(
        season_round=1,
        start_date="2014-01-05",
        end_date="2014-04-30",
        name="Round 1 2014"
    ).save()

    Season(
        season_round=2,
        start_date="2014-05-01",
        end_date="2014-08-31",
        name="Round 2 2014"
    ).save()


def create_player_data(apps, schema_editor):
    """
    Create 20 players in a loop
    """
    Player = apps.get_model("ladder", "Player")

    for n in range(1, 20):
        Player(
            first_name="Player",
            last_name="no " + n.__str__(),
            junior=False,
        ).save()


def create_ladder_data(apps, schema_editor):
    """
    Create two ladders for each season
    """
    Season = apps.get_model("ladder", "Season")
    Ladder = apps.get_model("ladder", "Ladder")

    for season in Season.objects.all():
        for n in range(1, 3):
            Ladder(
                ladder_type="First To 9",
                division=n.__str__(),
                season=season
            ).save()


def create_league_data(apps, schema_editor):
    """
    Create leagues, add half the players into each.
    """
    Ladder = apps.get_model("ladder", "Ladder")
    Player = apps.get_model("ladder", "Player")
    League = apps.get_model("ladder", "League")

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
    """
    Create results with a 50% play rate
    """
    Ladder = apps.get_model("ladder", "Ladder")
    Result = apps.get_model("ladder", "Result")

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
            name='Ladder',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('division', models.CharField(max_length=11)),
                ('ladder_type', models.CharField(max_length=100)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='League',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('sort_order', models.IntegerField(default=0)),
                ('ladder', models.ForeignKey(to='ladder.Ladder')),
            ],
            options={
                'ordering': ['sort_order'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Player',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('first_name', models.CharField(max_length=100)),
                ('last_name', models.CharField(max_length=100)),
                ('home_phone', models.CharField(max_length=100, blank=True)),
                ('mobile_phone', models.CharField(max_length=100, blank=True)),
                ('email', models.CharField(max_length=100, blank=True)),
                ('junior', models.BooleanField(default=None)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='league',
            name='player',
            field=models.ForeignKey(to='ladder.Player'),
            preserve_default=True,
        ),
        migrations.CreateModel(
            name='Result',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('result', models.IntegerField()),
                ('date_added', models.DateField(verbose_name='Date added')),
                ('inaccurate_flag', models.BooleanField(default=None)),
                ('ladder', models.ForeignKey(to='ladder.Ladder')),
                ('opponent', models.ForeignKey(to='ladder.Player')),
                ('player', models.ForeignKey(to='ladder.Player')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Season',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('name', models.CharField(max_length=150)),
                ('start_date', models.DateField(verbose_name='Start date')),
                ('end_date', models.DateField(verbose_name='End date')),
                ('season_round', models.IntegerField(max_length=1)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='ladder',
            name='season',
            field=models.ForeignKey(to='ladder.Season'),
            preserve_default=True,
        ),
        migrations.RunPython(create_season_data),
        migrations.RunPython(create_player_data),
        migrations.RunPython(create_ladder_data),
        migrations.RunPython(create_league_data),
        migrations.RunPython(create_result_data)
    ]
