from django.contrib.auth.models import User
from ladder.models import Season, Player, Ladder, League, Result
from rest_framework import serializers



class SeasonSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Season
        fields = ['name', 'start_date', 'end_date', 'season_round']


class PlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = ['id', 'first_name', 'last_name']


class PlayerDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = ['first_name', 'last_name', 'player_stats']


class PlayerDetailHeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = ['first_name', 'last_name', 'head']

class LadderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ladder
        fields = ['id', 'season', 'division', 'ladder_type']


class ResultPlayerSerializer(serializers.ModelSerializer):
    player = PlayerSerializer()
    class Meta:
        model = League
        fields = ['id', 'player']


class LeagueSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = League
        fields = ['ladder', 'player', 'sort_order']


class ResultSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Result
        fields = ['ladder', 'player', 'opponent', 'result', 'date_added', 'inaccurate_flag']
