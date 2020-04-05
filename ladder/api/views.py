from ladder.api.serializers import (
    SeasonSerializer,
    PlayerSerializer,
    LadderSerializer,
    LeagueSerializer,
    ResultSerializer
)
from ladder.models import Season, Player, Ladder, League, Result
from rest_framework import viewsets
from rest_framework import permissions


class SeasonViewSet(viewsets.ModelViewSet):
    queryset = Season.objects.all()
    serializer_class = SeasonSerializer
    permission_classes = [permissions.IsAuthenticated]


class PlayerViewSet(viewsets.ModelViewSet):
    queryset = Player.objects.all()
    serializer_class = PlayerSerializer
    permission_classes = [permissions.IsAuthenticated]


class LadderViewSet(viewsets.ModelViewSet):
    queryset = Ladder.objects.all()
    serializer_class = LadderSerializer
    permission_classes = [permissions.IsAuthenticated]


class LeagueViewSet(viewsets.ModelViewSet):
    queryset = League.objects.all()
    serializer_class = LeagueSerializer
    permission_classes = [permissions.IsAuthenticated]


class ResultViewSet(viewsets.ModelViewSet):
    queryset = Result.objects.all()
    serializer_class = ResultSerializer
    permission_classes = [permissions.IsAuthenticated]
