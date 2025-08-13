import datetime
import json

from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Max
from django.http import HttpResponseRedirect, Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.utils.html import escape
from django.views.decorators.cache import cache_page, never_cache
from django.contrib import messages


from ladder.forms import AddResultForm, AddEntryForm
from ladder.models import Ladder, Player, Result, Season, League, LadderSubscription


@cache_page(60 * 60 * 24 * 2, key_prefix='index')  # 2 day page cache
def index(request):
    current_season = Season.objects.latest('start_date')
    os_year = Season.objects.order_by('start_date')[0].start_date.year
    cs_year = current_season.start_date.year

    at_ladders = Season.objects.count()
    at_divisions = Ladder.objects.count()
    at_results = int(Result.objects.count() / 2)
    at_players = Player.objects.count()

    context = {
        'current_season': current_season,
        'at_years': (cs_year - os_year),
        'at_years_str': ' (' + os_year.__str__() + ' -> ' + cs_year.__str__() + ')',
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


def current_season_redirect(request):
    season_first = Season.objects.latest('start_date')

    return HttpResponseRedirect(reverse('season', args=(
        season_first.start_date.year, season_first.season_round)
    ))


def season(request, year, season_round):
    season_object = get_object_or_404(Season, start_date__year=year, season_round=season_round)

    # Optimize with prefetch_related to avoid N+1 queries
    ladders = Ladder.objects.filter(season=season_object).prefetch_related(
        'league_set__player__user'  # Prefetch leagues, players, and users
    )

    # Get all results for this season with related data in one query
    results = Result.objects.filter(
        ladder__season=season_object
    ).select_related(
        'player', 'opponent', 'ladder'
    )

    # Build results dictionary efficiently
    results_dict = {}
    for result in results:
        results_dict.setdefault(result.player.id, []).append(result)

    # No need to fetch league separately as it's prefetched
    return render(
        request, 'ladder/season/index.html',
        dict(season=season_object, ladders=ladders, results_dict=results_dict)
    )


def ladder(request, year, season_round, division_id):
    ladder_object = get_object_or_404(
        Ladder.objects.prefetch_related('league_set__player__user'),
        division=division_id,
        season__start_date__year=year,
        season__season_round=season_round
    )

    subscribed = False
    if request.user.is_authenticated and not request.user.is_superuser:
        subscribed = LadderSubscription.objects.filter(
            user=request.user,
            ladder__division=division_id,
            ladder__season__start_date__year=year,
            ladder__season__season_round=season_round
        ).exists()  # Use exists() instead of count() > 0

    # Optimize results query with select_related
    results = Result.objects.filter(ladder=ladder_object).select_related(
        'player', 'opponent'
    )

    results_dict = {}
    for result in results:
        results_dict.setdefault(result.player.id, []).append(result)

    return render(request, 'ladder/ladder/index.html',
                  {'ladder': ladder_object, 'results_dict': results_dict, 'subscribed': subscribed})

@login_required
@never_cache
def ladder_subscription(request, year, season_round, division_id):

    if request.user.is_superuser or not request.user.is_authenticated:
        return HttpResponseForbidden()

    existing_subscription = LadderSubscription.objects.filter(
        user=request.user,
        ladder__division=division_id,
        ladder__season__start_date__year=year,
        ladder__season__season_round=season_round
    )

    # unsubscribe
    if existing_subscription.count() > 0:
        existing_subscription.delete()
        messages.success(request, 'Unsubscribed from email notifications.')
        return HttpResponseRedirect(reverse('ladder', args=(year, season_round, division_id)))

    ladder_object = get_object_or_404(Ladder, division=division_id, season__start_date__year=year,
                                      season__season_round=season_round)

    # subscribe
    LadderSubscription(
        user=request.user,
        ladder=ladder_object,
        subscribed_at=datetime.datetime.now()
    ).save()

    messages.success(request, 'Subscribed to email notifications.')
    return HttpResponseRedirect(reverse('ladder', args=(year, season_round, division_id)))

@login_required
def add(request, year, season_round, division_id):
    if not request.user.is_superuser:
        return HttpResponseRedirect(reverse('ladder', args=(year, season_round, division_id)))

    ladder_object = get_object_or_404(Ladder, division=division_id, season__start_date__year=year,
                                      season__season_round=season_round)

    result = Result(ladder=ladder_object, date_added=datetime.datetime.now())

    try:
        next_ladder = Ladder.objects.get(season=ladder_object.season, division=ladder_object.division + 1)
    except Ladder.DoesNotExist:
        next_ladder = False

    try:
        previous_ladder = Ladder.objects.get(season=ladder_object.season, division=ladder_object.division - 1)
    except Ladder.DoesNotExist:
        previous_ladder = False


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

            return HttpResponseRedirect(reverse('add', args=(
                ladder_object.season.start_date.year, ladder_object.season.season_round, ladder_object.division)))
    else:
        form = AddResultForm(ladder_object, instance=result)

    # prepare the results for displaying
    results = Result.objects.filter(ladder=ladder_object)
    results_dict = {}
    for result in results:
        results_dict.setdefault(result.player.id, []).append(result)

    return render(request, 'ladder/ladder/add.html',
                  {'ladder': ladder_object, 'results_dict': results_dict, 'form': form,
                   'next_ladder': next_ladder, 'previous_ladder': previous_ladder})


def player_history(request, player_id):
    player = get_object_or_404(Player, pk=player_id)

    # Prefetch player results at the player level
    player = Player.objects.prefetch_related('result_player').get(pk=player_id)

    # Get league_set with comprehensive prefetching
    league_set = player.league_set.select_related(
        'ladder__season'
    ).prefetch_related(
        'ladder__league_set'  # For league counts
    ).order_by('-ladder__season__start_date')

    # Force evaluation of league_set to ensure prefetching works
    league_list = list(league_set)

    # Pre-calculate player stats
    player_stats = player.player_stats()

    # Return top 10 played against
    try:
        head = Result.objects.values('opponent', 'opponent__first_name', 'opponent__last_name').filter(
            player=player).annotate(times_played=Count('opponent'), last_played=Max('date_added')).order_by(
            '-times_played')[:10]
    except Result.DoesNotExist:
        raise Http404

    return render(request, 'ladder/player/history.html', {
        'player': player,
        'league_set': league_list,  # Use the evaluated list
        'ladder_set': league_list,
        'head': head,
        'player_stats': player_stats
    })


def head_to_head(request, player_id, opponent_id):
    player = get_object_or_404(Player, pk=player_id)
    opponent = get_object_or_404(Player, pk=opponent_id)

    results1 = Result.objects.filter(player=player, opponent=opponent, result__lt=9).order_by(
        '-ladder__season__end_date')
    results2 = Result.objects.filter(player=opponent, opponent=player, result__lt=9).order_by(
        '-ladder__season__end_date')

    results = results1 | results2

    stats = {'won': results2.count(), 'lost': results1.count(), 'played': results1.count() + results2.count()}

    return render(request, 'ladder/head_to_head/index.html',
                  {'stats': stats, 'results': results, 'player': player, 'opponent': opponent})


def player_result(request):
    query = request.GET.get('player_name', False)
    if query is False:
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
    result_set = {}
    query = request.GET.get('query', False)
    if query is False:
        raise Http404

    qs = Player.objects.all()

    for term in query.split():
        qs = qs.filter(Q(first_name__icontains=term) | Q(last_name__icontains=term))

    results = [escape(x.first_name.strip() + ' ' + x.last_name.strip()) for x in qs]
    result_set["options"] = results

    return HttpResponse(json.dumps(result_set), content_type="application/json")


def h2h_search(request, player_id):
    result_set = {}
    query = request.GET.get('query', False)
    if query is False:
        raise Http404

    head = Result.objects.values('opponent', 'opponent__first_name', 'opponent__last_name')

    for term in query.split():
        head = head.filter(
            Q(opponent__first_name__icontains=term) | Q(opponent__last_name__icontains=term),
            Q(player__id=player_id)).annotate(times_played=Count('opponent')).order_by('-times_played')

    results = {}
    for x in head:
        results[x['opponent']] = escape(
            str(x['times_played']).strip() + ' x ' + x['opponent__first_name'].strip() + ' ' + x[
                'opponent__last_name'].strip())

    result_set["options"] = results

    return HttpResponse(json.dumps(result_set), content_type="application/json")


def season_ajax_stats(request):

    season_id = request.GET.get('id', False)
    if season_id is False:
        raise Http404

    try:
        season_object = Season.objects.get(pk=season_id)
    except Season.DoesNotExist:
        raise Http404
    except ValueError:
        raise Http404

    stats = season_object.get_stats()

    include_leader = request.GET.get('leader', False)
    if include_leader:
        stats.update(season_object.get_leader_stats(user=request.user))

    return HttpResponse(json.dumps(stats), content_type="application/json")


def season_ajax_progress(request):
    season_id = request.GET.get('id', False)
    if season_id is False:
        raise Http404

    try:
        season_object = Season.objects.get(pk=season_id)
    except Season.DoesNotExist:
        raise Http404
    except ValueError:
        raise Http404

    return HttpResponse(json.dumps(season_object.get_progress()), content_type="application/json")

@login_required
def result_entry(request):
    user_object = request.user
    try:
        ladder_object = Ladder.objects.filter(league__player__user=user_object).order_by('-id')[0]
    except IndexError:
        raise Http404

    result = Result(ladder=ladder_object, date_added=datetime.datetime.now())
    form = AddEntryForm(ladder_object, user_object, instance=result)

    return render(request, 'ladder/result/entry.html', {
        'user': user_object,
        'ladder': ladder_object,
        'form': form,
        'is_closed': ladder_object.is_closed()
    })

@login_required
def result_entry_add(request):
    user = request.user
    ladder_object = Ladder.objects.filter(league__player__user=user).order_by('-id')[0]
    result = Result(ladder=ladder_object, date_added=datetime.datetime.now(), inaccurate_flag=0)

    form = AddEntryForm(ladder_object, user, request.POST, instance=result)

    if form.is_valid():
        user_result = form.save(commit=False)
        is_user_winner = form.cleaned_data['winner'] == 1
        losing_result = form.cleaned_data['result']

        # check for existing results, assume update if find a match aka delete
        try:
            existing_player_result = Result.objects.get(ladder=ladder_object, player=user_result.player,
                                                        opponent=user_result.opponent)
            existing_player_result.delete()
            existing_opponent_result = Result.objects.get(ladder=ladder_object, player=user_result.opponent,
                                                          opponent=user_result.player)
            existing_opponent_result.delete()
        except Result.DoesNotExist:
            pass

        # build the mirror result (aka opponent) from losing form data
        opponent_result = Result(ladder=user_result.ladder, player=user_result.opponent,
                                opponent=user_result.player, result=9, date_added=user_result.date_added,
                                inaccurate_flag=user_result.inaccurate_flag)

        # switch flag if user is winner
        if is_user_winner:
            opponent_result.result = losing_result
            user_result.result = 9

        user_result.save()
        opponent_result.save()

        return HttpResponseRedirect(reverse('ladder', args=(
            ladder_object.season.start_date.year, ladder_object.season.season_round, ladder_object.division)))

    return render(request, 'ladder/result/entry.html', {
        'user': user,
        'ladder': ladder_object,
        'form': form
    })


def unsubscribe_token(request, token):
    """Public unsubscribe via token - no login required"""
    subscription = get_object_or_404(LadderSubscription, unsubscribe_token=token)

    # Extract division details
    ladder = subscription.ladder
    year = ladder.season.start_date.year
    season_round = ladder.season.season_round
    division_id = ladder.division

    # Delete the subscription
    subscription.delete()

    # Add success message and redirect to the ladder (division) page
    messages.success(request, f'Successfully unsubscribed from {ladder} email notifications.')
    return HttpResponseRedirect(reverse('ladder', args=(year, season_round, division_id)))
