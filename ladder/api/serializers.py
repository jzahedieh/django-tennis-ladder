from ladder.models import Season, Player, Ladder, League, Result
from rest_framework import serializers


class SeasonSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Season
        fields = ['name', 'start_date', 'end_date', 'season_round']


class PlayerSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Player
        fields = ['first_name', 'last_name']


class LadderSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Ladder
        fields = ['season', 'division', 'ladder_type']


class LeagueSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = League
        fields = ['ladder', 'player', 'sort_order']


class ResultSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Result
        fields = ['ladder', 'player', 'opponent', 'result', 'date_added', 'inaccurate_flag']
