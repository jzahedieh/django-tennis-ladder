from __future__ import division
import datetime
import json

from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.utils.html import escape
from django.core.urlresolvers import reverse
from django.views.decorators.cache import cache_page
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Max
from django.views.decorators.gzip import gzip_page

from ladder.models import Ladder, Player, Result, Season, League
from ladder.forms import AddResultForm


@gzip_page
@cache_page(60 * 60 * 24 * 2, key_prefix=u'index')  # 2 day page cache
def index(request):
    current_season = Season.objects.latest(u'start_date')
    os_year = Season.objects.order_by(u'start_date')[0].start_date.year
    cs_year = current_season.start_date.year

    at_ladders = Season.objects.count()
    at_divisions = Ladder.objects.count()
    at_results = int(Result.objects.count() / 2)
    at_players = Player.objects.count()

    context = {
        u'current_season': current_season,
        u'at_years': (cs_year - os_year),
        u'at_years_str': u' (' + os_year.__str__() + u' -> ' + cs_year.__str__() + u')',
        u'at_divisions': at_divisions,
        u'at_ladders': at_ladders,
        u'at_results': at_results,
        u'at_players': at_players,
    }
    return render(request, u'ladder/index.html', context)


@gzip_page
@cache_page(60 * 60 * 24, key_prefix=u'round')  # 1 day page cache
def list_rounds(request):
    seasons = Season.objects.order_by(u'-start_date')
    context = {
        u'seasons': seasons,
    }
    return render(request, u'ladder/season/list.html', context)


@gzip_page
@cache_page(60 * 60, key_prefix=u'season')  # 1 hour page cache
def season(request, year, season_round):
    season_object = get_object_or_404(Season, start_date__year=year, season_round=season_round)

    ladders = Ladder.objects.filter(season=season_object)

    results = Result.objects.filter(ladder__season=season_object)
    league = League.objects.filter(ladder__season=season_object)

    results_dict = {}

    for result in results:
        results_dict.setdefault(result.player.id, []).append(result)

    return render(
        request, u'ladder/season/index.html',
        dict(season=season_object, ladders=ladders, results_dict=results_dict, league=league)
    )


@gzip_page
def ladder(request, year, season_round, division_id):
    ladder_object = get_object_or_404(Ladder, division=division_id, season__start_date__year=year,
                                      season__season_round=season_round)

    results = Result.objects.filter(ladder=ladder_object)

    results_dict = {}

    for result in results:
        results_dict.setdefault(result.player.id, []).append(result)

    return render(request, u'ladder/ladder/index.html', {u'ladder': ladder_object, u'results_dict': results_dict})


@login_required
def add(request, year, season_round, division_id):
    ladder_object = get_object_or_404(Ladder, division=division_id, season__start_date__year=year,
                                      season__season_round=season_round)

    result = Result(ladder=ladder_object, date_added=datetime.datetime.now())

    # process or generate te score adding form
    if request.POST:
        form = AddResultForm(ladder_object, request.POST, instance=result)
        if form.is_valid():
            losing_result = form.save(commit=False)

            # check for existing results, assume update if find a match aka delete
            try:
                existing_player_result = Result.objects.get(ladder=ladder_object, player=losing_result.player,
                                                            opponent=losing_result.opponent)
                existing_player_result.delete()
                existing_opponent_result = Result.objects.get(ladder=ladder_object, player=losing_result.opponent,
                                                              opponent=losing_result.player)
                existing_opponent_result.delete()
            except Result.DoesNotExist:
                pass

            # build the mirror result (aka winner) from losing form data
            winning_result = Result(ladder=losing_result.ladder, player=losing_result.opponent,
                                    opponent=losing_result.player, result=9, date_added=losing_result.date_added,
                                    inaccurate_flag=losing_result.inaccurate_flag)
            losing_result.save()
            winning_result.save()

            return HttpResponseRedirect(reverse(u'ladder:add', args=(
                ladder_object.season.start_date.year, ladder_object.season.season_round, ladder_object.division)))
    else:
        form = AddResultForm(ladder_object, instance=result)

    # prepare the results for displaying
    results = Result.objects.filter(ladder=ladder_object)
    results_dict = {}
    for result in results:
        results_dict.setdefault(result.player.id, []).append(result)

    return render(request, u'ladder/ladder/add.html',
                  {u'ladder': ladder_object, u'results_dict': results_dict, u'form': form})


@gzip_page
def player_history(request, player_id):
    player = get_object_or_404(Player, pk=player_id)
    league_set = player.league_set.order_by(u'-ladder__season__start_date')

    #return top 10 played against
    try:
        head = Result.objects.values(u'opponent', u'opponent__first_name', u'opponent__last_name').filter(
            player=player).annotate(times_played=Count(u'opponent'), last_played=Max(u'date_added')).order_by(
                u'-times_played')[:10]
    except Result.DoesNotExist:
        raise Http404

    return render(request, u'ladder/player/history.html',
                  {u'player': player, u'league_set': league_set, u'ladder_set': league_set, u'head': head})


@gzip_page
def head_to_head(request, player_id, opponent_id):
    player = get_object_or_404(Player, pk=player_id)
    opponent = get_object_or_404(Player, pk=opponent_id)

    results1 = Result.objects.filter(player=player, opponent=opponent, result__lt=9).order_by(
        u'-ladder__season__end_date')
    results2 = Result.objects.filter(player=opponent, opponent=player, result__lt=9).order_by(
        u'-ladder__season__end_date')

    results = results1 | results2

    stats = {u'won': results2.count(), u'lost': results1.count(), u'played': results1.count() + results2.count()}

    return render(request, u'ladder/head_to_head/index.html',
                  {u'stats': stats, u'results': results, u'player': player, u'opponent': opponent})


@gzip_page
def player_result(request):
    query = request.GET.get(u'player_name', False)
    if query is False:
        raise Http404

    qs = Player.objects.all()

    for term in query.split():
        qs = qs.filter(Q(first_name__icontains=term) | Q(last_name__icontains=term))

    results = [x for x in qs]

    if len(results) == 1:
        player = results[0]
        return player_history(request, player.id)

    return render(request, u'ladder/player/results.html', {u'players': results, u'query': escape(query)})


def player_search(request):
    result_set = {}
    query = request.GET.get(u'query', False)
    if query is False:
        raise Http404

    qs = Player.objects.all()

    for term in query.split():
        qs = qs.filter(Q(first_name__icontains=term) | Q(last_name__icontains=term))

    results = [escape(x.first_name.strip() + u' ' + x.last_name.strip()) for x in qs]
    result_set[u"options"] = results

    return HttpResponse(json.dumps(result_set), content_type=u"application/json")


def h2h_search(request, player_id):
    result_set = {}
    query = request.GET.get(u'query', False)
    if query is False:
        raise Http404

    head = Result.objects.values(u'opponent', u'opponent__first_name', u'opponent__last_name')

    for term in query.split():
        head = head.filter(
            Q(opponent__first_name__icontains=term) | Q(opponent__last_name__icontains=term),
            Q(player__id=player_id)).annotate(times_played=Count(u'opponent')).order_by(u'-times_played')

    results = {}
    for x in head:
        results[x[u'opponent']] = escape(
            unicode(x[u'times_played']).strip() + u' x ' + x[u'opponent__first_name'].strip() + u' ' + x[
                u'opponent__last_name'].strip())

    result_set[u"options"] = results

    return HttpResponse(json.dumps(result_set), content_type=u"application/json")


def season_ajax_stats(request):

    season_id = request.GET.get(u'id', False)
    if season_id is False:
        raise Http404

    try:
        season_object = Season.objects.get(pk=season_id)
    except Season.DoesNotExist:
        raise Http404
    except ValueError:
        raise Http404

    stats = season_object.get_stats()

    include_leader = request.GET.get(u'leader', False)
    if include_leader:
        stats.update(season_object.get_leader_stats())

    return HttpResponse(json.dumps(stats), content_type=u"application/json")


def season_ajax_progress(request):
    season_id = request.GET.get(u'id', False)
    if season_id is False:
        raise Http404

    try:
        season_object = Season.objects.get(pk=season_id)
    except Season.DoesNotExist:
        raise Http404
    except ValueError:
        raise Http404

    return HttpResponse(json.dumps(season_object.get_progress()), content_type=u"application/json")