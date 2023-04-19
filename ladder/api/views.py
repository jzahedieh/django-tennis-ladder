import datetime

from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.views import APIView
from rest_framework_simplejwt import authentication

from ladder.api.serializers import (
    SeasonSerializer,
    PlayerSerializer,
    LadderSerializer,
    LeagueSerializer,
    ResultSerializer, ResultPlayerSerializer, PlayerDetailSerializer, PlayerDetailHeadSerializer
)
from ladder.models import Season, Player, Ladder, League, Result
from rest_framework import permissions, viewsets


class ResultPlayerViewSet(viewsets.ViewSet):
    # todo: custom permission class
    permission_classes = [IsAuthenticated]

    # todo: validation, if current ladder closed cannot enter result

    def list(self, request):
        # get latest league for current user
        league = League.objects.all().filter(player__user=request.user).last()

        # get all players from latest league excluding current user player
        # queryset = League.objects.all().filter(ladder=league.ladder).exclude(player__user=request.user)
        # serializer = ResultPlayerSerializer(queryset, many=True)
        league_opponents = League.objects.values_list('player_id', flat=True).filter(ladder=league.ladder).exclude(player__user=request.user)
        queryset = Player.objects.all().filter(id__in=league_opponents)
        serializer = PlayerSerializer(queryset, many=True)
        return Response({"ladder_id": league.ladder_id, "opponents": serializer.data})

    @action(detail=False, methods=['post'])
    def submit(self, request):
        user = request.user
        player = Player.objects.filter(user=user).first()

        # todo: use serializer class and put in action
        opponent_id = request.data['opponent_id']
        win = request.data['win']
        result = request.data['result']
        ladder_id = request.data['ladder_id']

        player_result = Result.objects.filter(player=player, opponent_id=opponent_id).first()
        opponent_result = Result.objects.filter(player_id=opponent_id, opponent=player).first()

        if not player_result:
            Result.objects.create(
                result=9 if win else result, player=player, opponent_id=opponent_id, ladder_id=ladder_id,
                date_added=datetime.datetime.now()
            )
        else:
            player_result.result = 9 if win else result
            player_result.date_added = datetime.datetime.now()
            player_result.save()
        if not opponent_result:
            Result.objects.create(
                result=result if win else 9, player_id=opponent_id, opponent=player, ladder_id=ladder_id,
                date_added=datetime.datetime.now()
            )
        else:
            opponent_result.result = result if win else 9
            opponent_result.date_added = datetime.datetime.now()
            opponent_result.save()

        return Response({'status': 'saved'})


class SeasonViewSet(viewsets.ModelViewSet):
    queryset = Season.objects.all()
    serializer_class = SeasonSerializer
    permission_classes = [permissions.DjangoModelPermissionsOrAnonReadOnly]


class PlayerViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    def list(self, request):
        queryset = Player.objects.all()
        serializer = PlayerSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        queryset = Player.objects.all()
        player = get_object_or_404(queryset, pk=pk)
        serializer = PlayerDetailSerializer(player)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def head_to_head(self, request, pk=None):
        queryset = Player.objects.all()
        player = get_object_or_404(queryset, pk=pk)
        serializer = PlayerDetailHeadSerializer(player)
        return Response(serializer.data)

class LadderViewSet(viewsets.ModelViewSet):
    queryset = Ladder.objects.all()
    serializer_class = LadderSerializer
    permission_classes = [permissions.DjangoModelPermissionsOrAnonReadOnly]


class LeagueViewSet(viewsets.ModelViewSet):
    queryset = League.objects.all()
    serializer_class = LeagueSerializer
    permission_classes = [permissions.DjangoModelPermissionsOrAnonReadOnly]


class ResultViewSet(viewsets.ModelViewSet):
    queryset = Result.objects.all()
    serializer_class = ResultSerializer
    permission_classes = [permissions.IsAdminUser]
