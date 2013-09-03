import datetime

from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.utils import simplejson as json
from django.utils.html import escape
from django.core.urlresolvers import reverse
from django.views.decorators.cache import cache_page
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from ladder.models import Ladder, Player, Result, Season, League


@cache_page(60 * 60 * 24 * 2, key_prefix='index')  # 2 day page cache
def index(request):
    current_season = Season.objects.order_by('-start_date')[0]
    os_year = Season.objects.order_by('start_date')[0].start_date.year
    cs_year = current_season.start_date.year

    at_ladders = Season.objects.count()
    at_divisions = Ladder.objects.count()
    at_results = Result.objects.count() / 2
    at_players = Player.objects.count()

    context = {
        'current_season': current_season,
        'at_years': (cs_year - os_year),
        'at_years_str': ' (' + os_year.__str__() +  ' -> ' + cs_year.__str__() +  ')',
        'at_divisions': at_divisions,
        'at_ladders': at_ladders,
        'at_results': at_results,
        'at_players': at_players,
    }
    return render(request, 'ladder/index.html', context)


@cache_page(60 * 60 * 24, key_prefix='round')  # 1 day page cache
def list_rounds(request):
    seasons = Season.objects.order_by('-start_date')
    context = {
        'seasons': seasons,
    }
    return render(request, 'ladder/season/list.html', context)


@cache_page(60 * 60, key_prefix='season')  # 1 hour page cache
def season(request, year, season_round):
    season = get_object_or_404(Season, start_date__year=year, season_round=season_round)

    ladders = Ladder.objects.filter(season=season)

    results = Result.objects.filter(ladder__season=season)
    league = League.objects.filter(ladder__season=season)

    results_dict = {}

    for result in results:
        results_dict.setdefault(result.player.id, []).append(result)

    return render(request, 'ladder/season/index.html',
                  dict(season=season, ladders=ladders, results_dict=results_dict, league=league)
    )


def ladder(request, year, season_round, division_id):
    ladder = get_object_or_404(Ladder, division=division_id, season__start_date__year=year, season__season_round=season_round)

    results = Result.objects.filter(ladder=ladder)

    results_dict = {}

    for result in results:
        results_dict.setdefault(result.player.id, []).append(result)

    return render(request, 'ladder/ladder/index.html', {'ladder': ladder, 'results_dict': results_dict})

@login_required
def add(request, year, season_round, division_id):
    ladder = get_object_or_404(Ladder, division=division_id, season__start_date__year=year, season__season_round=season_round)

    results = Result.objects.filter(ladder=ladder)

    results_dict = {}

    for result in results:
        results_dict.setdefault(result.player.id, []).append(result)

    return render(request, 'ladder/ladder/add.html', {'ladder': ladder, 'results_dict': results_dict, 'points': range(10)})

@login_required
def add_result(request, ladder_id):
    ladder = get_object_or_404(Ladder, pk=ladder_id)
    try:
        inaccurate = request.POST['checkbox_inaccurate']
    except:
        inaccurate = 0

    try:
        player_object = Player.objects.get(id=request.POST['player'])
        opponent_object = Player.objects.get(id=request.POST['opponent'])
        player_score = request.POST['player_score']
        opponent_score = request.POST['opponent_score']

        if int(player_score) != 9 and int(opponent_score) != 9:
            raise Exception("No winner selected")

        if int(player_score) == 9 and int(opponent_score) == 9:
            raise Exception("Can't have two winners")

        try:
            result_object = Result.objects.get(ladder=ladder, player=player_object, opponent=opponent_object)
            result_object.delete()
            raise Exception("want to add all the time")
        except:
            player_result_object = Result(ladder=ladder, player=player_object, opponent=opponent_object,
                                       result=player_score, date_added=datetime.datetime.now(), inaccurate_flag=inaccurate)
            player_result_object.save()


        try:
            result_object = Result.objects.get(ladder=ladder, player=opponent_object, opponent=player_object)
            result_object.delete()
            raise Exception("want to add all the time")
        except:
            opp_result_object = Result(ladder=ladder, player=opponent_object, opponent=player_object,
                                       result=opponent_score, date_added=datetime.datetime.now(), inaccurate_flag=inaccurate)
            opp_result_object.save()


    except Exception as e:
        return render(request, 'ladder/ladder/add.html', {
            'ladder': ladder,
            'error_message': e,
            'points': range(10)
        })
    else:
                return HttpResponseRedirect(
            reverse('ladder:add', args=(ladder.season.start_date.year, ladder.season.season_round, ladder.division)))


def player_history(request, player_id):
    try:
        player = Player.objects.get(pk=player_id)
        league_set = player.league_set.order_by('-ladder__season__start_date')
    except Player.DoesNotExist:
        raise Http404

    return render(request, 'ladder/player/history.html', {'player': player, 'league_set': league_set, 'ladder_set':league_set})


def player_result(request):
    try:
        query = request.GET[u'player_name']
    except:
        raise Http404

    qs = Player.objects.all()

    for term in query.split():
        qs = qs.filter(Q(first_name__icontains=term) | Q(last_name__icontains=term))

    results = [x for x in qs]

    if len(results) == 1:
        player = results[0]
        return player_history(request, player.id)

    return render(request, 'ladder/player/results.html', {'players': results, 'query': escape(query)})


def player_search(request):
    resultSet = {}
    try:
        query = request.GET[u'query']
    except:
        raise Http404

    qs = Player.objects.all()

    for term in query.split():
        qs = qs.filter(Q(first_name__icontains=term) | Q(last_name__icontains=term))

    results = [escape(x.first_name.strip() + ' ' + x.last_name.strip()) for x in qs]
    resultSet["options"] = results

    return HttpResponse(json.dumps(resultSet), content_type="application/json")


def season_ajax_stats(request):
    try:
        season_id = request.GET[u'id']
    except:
        raise Http404

    try:
        season = Season.objects.get(pk=season_id)
    except Season.DoesNotExist:
        raise Http404
    except ValueError:
        raise Http404

    stats = season.get_stats()

    try:
        include_leader = request.GET[u'leader']
        if include_leader:
            stats.update(season.get_leader_stats())
    except:
        pass

    return HttpResponse(json.dumps(stats), content_type="application/json")